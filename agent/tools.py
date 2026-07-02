"""Agent tools: RAG search, quiz generation, workflow synthesis, web search."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "retrieval"))

import anthropic
import requests
from dotenv import load_dotenv
from retriever import Retriever

load_dotenv()

MODEL = "claude-sonnet-4-6"
TAVILY_URL = "https://api.tavily.com/search"

_retriever = None
_client = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def search_notes(query: str, cert_filter: str | None = None, top_k: int = 5) -> str:
    retriever = _get_retriever()
    results = retriever.search(query, cert_filter=cert_filter, top_k=top_k)
    if not results:
        return "No relevant content found in your Qualys notes for this query."
    return retriever.format_context(results)


def quiz_me(topic: str, question_type: str = "recall") -> dict:
    context = search_notes(topic, top_k=8)
    system = (
        "Generate ONE quiz question as JSON only: {question: str, model_answer: str, source: str}. "
        f"question_type: {question_type}. Return raw JSON, no markdown."
    )

    for _ in range(2):
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": context}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue

    return {"question": "Parse error", "model_answer": "", "source": ""}


def suggest_workflow(task_description: str, cert_filter: str | None = None) -> str:
    context = search_notes(task_description, cert_filter, top_k=6)
    instruction = (
        f"Using ONLY the context, write numbered steps for: {task_description}. "
        "Flag gaps with [NOTE: limited info]. End with Source: {cert_name}/{h1}"
    )

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Context:\n{context}\n\n{instruction}"}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def web_search(query: str, max_results: int = 5) -> str:
    try:
        resp = requests.post(
            TAVILY_URL,
            json={"api_key": os.environ.get("TAVILY_API_KEY"), "query": query, "max_results": max_results},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return f"Web search unavailable: {e}"

    return "\n".join(
        f"[Web] {r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}\n---"
        for r in data.get("results", [])
    )
