"""LangGraph agent: classify intent, run the matching tool, generate a grounded response."""

import operator
import sqlite3
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "retrieval"))

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from prompts import SYSTEM_PROMPT
from tools import quiz_me, search_notes, suggest_workflow, web_search

load_dotenv()

MODEL = "claude-sonnet-4-6"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"

chat_model = ChatAnthropic(model=MODEL, max_tokens=1024)


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    tool_called: str
    context: str
    session_id: str
    cert_filter: str | None


def classify_intent(state: AgentState) -> dict:
    message = state["messages"][-1]["content"]

    cert_filter = state.get("cert_filter")
    if message.startswith("In VMDR:"):
        cert_filter = "VMDR"
    elif message.startswith("In VMF:"):
        cert_filter = "VMF"

    lowered = message.lower()
    if any(p in lowered for p in ("quiz me", "test me", "give me a question")):
        tool_called = "quiz_me"
    elif any(p in lowered for p in ("how do i", "steps to", "workflow for", "set up", "configure")):
        tool_called = "suggest_workflow"
    elif any(p in lowered for p in ("search the web", "search online", "look up online")):
        tool_called = "web_search"
    else:
        tool_called = "search_notes"

    return {"tool_called": tool_called, "cert_filter": cert_filter}


def run_search_notes(state: AgentState) -> dict:
    query = state["messages"][-1]["content"]
    result = search_notes(query, cert_filter=state["cert_filter"])
    tool_called = "web_search_fallback" if result.startswith("No relevant") else state["tool_called"]
    return {"context": result, "tool_called": tool_called}


def run_quiz_me(state: AgentState) -> dict:
    message = state["messages"][-1]["content"]
    topic = message
    for marker in ("quiz me on", "test me on", "give me a question on"):
        idx = message.lower().find(marker)
        if idx != -1:
            topic = message[idx + len(marker):].strip()
            break

    result = quiz_me(topic)
    formatted = f"Question: {result['question']}\n\nTake your time — reply when ready."
    return {"context": formatted}


def run_suggest_workflow(state: AgentState) -> dict:
    task = state["messages"][-1]["content"]
    result = suggest_workflow(task, cert_filter=state["cert_filter"])
    return {"context": result}


def run_web_search(state: AgentState) -> dict:
    result = web_search(state["messages"][-1]["content"])
    return {"context": result}


def generate_response(state: AgentState, config: RunnableConfig) -> dict:
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + state["messages"]
        + [{"role": "user", "content": "Context:" + state["context"]}]
    )

    response = chat_model.invoke(messages, config=config)

    return {"messages": [{"role": "assistant", "content": response.content}]}


graph = StateGraph(AgentState)
graph.add_node("classify_intent", classify_intent)
graph.add_node("run_search_notes", run_search_notes)
graph.add_node("run_quiz_me", run_quiz_me)
graph.add_node("run_suggest_workflow", run_suggest_workflow)
graph.add_node("run_web_search", run_web_search)
graph.add_node("generate_response", generate_response)

graph.set_entry_point("classify_intent")

graph.add_conditional_edges(
    "classify_intent",
    lambda state: state["tool_called"],
    {
        "search_notes": "run_search_notes",
        "quiz_me": "run_quiz_me",
        "suggest_workflow": "run_suggest_workflow",
        "web_search": "run_web_search",
    },
)

graph.add_conditional_edges(
    "run_search_notes",
    lambda state: "run_web_search" if state["tool_called"] == "web_search_fallback" else "generate_response",
    {
        "run_web_search": "run_web_search",
        "generate_response": "generate_response",
    },
)

graph.add_edge("run_quiz_me", "generate_response")
graph.add_edge("run_suggest_workflow", "generate_response")
graph.add_edge("run_web_search", "generate_response")
graph.add_edge("generate_response", END)

checkpointer = SqliteSaver(sqlite3.connect(str(DB_PATH), check_same_thread=False))
agent_graph = graph.compile(checkpointer=checkpointer)
