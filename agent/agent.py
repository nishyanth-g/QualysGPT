"""Single entry point for the QualysGPT agent, used by the UI and MCP server."""

import sys
from pathlib import Path
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph import DB_PATH, agent_graph, graph


def run(user_message: str, session_id: str, cert_filter: str | None = None) -> str:
    config = {"configurable": {"thread_id": session_id}}
    input_state = {
        "messages": [{"role": "user", "content": user_message}],
        "session_id": session_id,
        "cert_filter": cert_filter,
        "tool_called": "",
        "context": "",
    }
    result = agent_graph.invoke(input_state, config=config)
    return result["messages"][-1]["content"]


async def astream_events(user_message: str, session_id: str, config: dict) -> AsyncGenerator[str, None]:
    input_state = {
        "messages": [{"role": "user", "content": user_message}],
        "session_id": session_id,
        "cert_filter": None,
        "tool_called": "",
        "context": "",
    }
    async with AsyncSqliteSaver.from_conn_string(str(DB_PATH)) as checkpointer:
        stream_graph = graph.compile(checkpointer=checkpointer)
        async for event in stream_graph.astream_events(input_state, config=config, version="v2"):
            if event["event"] == "on_chat_model_stream":
                yield event["data"]["chunk"].content
