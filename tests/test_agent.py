"""Plain script exercising the full agent via agent.run(). Exit code 1 if a required test fails."""

import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "agent")

from agent import run
from graph import get_agent_graph, reformulate_query

SESSION_ID = "test-session-day4"
CONFIG = {"configurable": {"thread_id": SESSION_ID}}
exit_code = 0


def get_state():
    return get_agent_graph().get_state(CONFIG).values


def check(label: str, condition: bool):
    global exit_code
    print(("PASS" if condition else "FAIL") + " - " + label)
    if not condition:
        exit_code = 1


print("=== 1. Factual Q&A ===")
response = run("What is a QID?", session_id=SESSION_ID)
tool_called = get_state()["tool_called"]
print(f"tool_called: {tool_called}")
print(response[:200])
check("search_notes was called", tool_called == "search_notes")
check("response non-empty", bool(response.strip()))

print("\n=== 2. Quiz ===")
response = run("Quiz me on VMDR asset tagging", session_id=SESSION_ID)
tool_called = get_state()["tool_called"]
print(f"tool_called: {tool_called}")
print(response[:200])
check("quiz_me was called", tool_called == "quiz_me")
check("question in response", "question" in response.lower() or "?" in response)

print("\n=== 3. Workflow ===")
response = run("How do I set up an authenticated scan?", session_id=SESSION_ID)
tool_called = get_state()["tool_called"]
print(f"tool_called: {tool_called}")
print(response[:200])
check("suggest_workflow was called", tool_called == "suggest_workflow")
check("numbered steps in response", bool(re.search(r"(?m)^\s*\d+[.)]", response)))

print("\n=== 4. Web search ===")
response = run("Search the web for latest Qualys VMDR release notes", session_id=SESSION_ID)
tool_called = get_state()["tool_called"]
print(f"tool_called: {tool_called}")
print(response[:200])
check("web_search was called", tool_called == "web_search")

print("\n=== 5. Follow-up ===")
run("What is a QID?", session_id=SESSION_ID)
message_count_before = len(get_state()["messages"])

followup_response = run("Can you give more detail on that?", session_id=SESSION_ID)
tool_called = get_state()["tool_called"]
message_count_after = len(get_state()["messages"])
print(f"tool_called: {tool_called}")
print(followup_response[:300])
check(
    "response references prior context (conversation history carried forward)",
    message_count_after == message_count_before + 2,
)

print("\n=== 6. Web search synthesis (no deflection) ===")
response = run("Search the web for the latest CISA KEV additions", session_id=SESSION_ID)
tool_called = get_state()["tool_called"]
print(f"tool_called: {tool_called}")
print(response[:300])
deflection_phrases = ["i can only help with", "please visit", "check these links", "check the link", "check these sources"]
check("web_search was called", tool_called == "web_search")
check("response contains a URL", bool(re.search(r"https?://\S+", response)))
check("no deflection phrasing", not any(p in response.lower() for p in deflection_phrases))

print("\n=== 7. Query reformulation: standalone passthrough ===")
standalone_query = reformulate_query([{"role": "user", "content": "What is TruRisk?"}])
print(f"reformulated: {standalone_query}")
check("standalone query preserves topic (TruRisk)", "trurisk" in standalone_query.lower())

print("\n=== 8. Query reformulation: follow-up resolves context ===")
followup_query = reformulate_query([
    {"role": "user", "content": "What is TruRisk?"},
    {"role": "assistant", "content": "TruRisk is Qualys's risk-scoring framework. It's built from two main TruRisk factors: 1) the CVSS-based technical severity, and 2) the asset criticality score assigned to the host."},
    {"role": "user", "content": "tell me more about the second one"},
])
print(f"reformulated: {followup_query}")
check("follow-up reformulation contains 'TruRisk'", "trurisk" in followup_query.lower())

sys.exit(exit_code)
