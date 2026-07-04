"""FastMCP server exposing QualysGPT's agent tools over stdio."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from fastmcp import FastMCP
from tools import search_notes, quiz_me, suggest_workflow, web_search

mcp = FastMCP("QualysGPT")


@mcp.tool()
def qualys_search_notes(query: str, cert_filter: str = None) -> str:
    """Search Qualys certification notes for answers to security questions."""
    return search_notes(query, cert_filter=cert_filter)


@mcp.tool()
def qualys_quiz_me(topic: str, question_type: str = "recall") -> str:
    """Generate a quiz question from Qualys certification notes on a given topic."""
    result = quiz_me(topic, question_type)
    return f"Question: {result['question']}\n\nModel Answer: {result['model_answer']}"


@mcp.tool()
def qualys_suggest_workflow(task_description: str, cert_filter: str = None) -> str:
    """Generate a step-by-step Qualys workflow for a security task."""
    return suggest_workflow(task_description, cert_filter=cert_filter)


@mcp.tool()
def qualys_web_search(query: str) -> str:
    """Search the web for live Qualys documentation or CVE information."""
    return web_search(query)


if __name__ == "__main__":
    mcp.run()
