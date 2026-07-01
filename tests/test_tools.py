"""Plain script exercising agent/tools.py. Exit code 1 if a required test fails."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

import tools

exit_code = 0

print("=== search_notes ===")
for query in ["What is a QID?", "How do I create an asset group?"]:
    result = tools.search_notes(query)
    print(f"Query: {query}")
    print(result[:200])
    if isinstance(result, str) and len(result) > 0:
        print("PASS\n")
    else:
        print("FAIL\n")
        exit_code = 1

print("=== quiz_me ===")
quiz = tools.quiz_me("VMDR asset tagging")
print(f"Question: {quiz.get('question')}")
print(f"Answer: {quiz.get('model_answer')}")
if quiz.get("question") and quiz.get("model_answer"):
    print("PASS\n")
else:
    print("FAIL\n")
    exit_code = 1

print("=== suggest_workflow ===")
workflow = tools.suggest_workflow("set up an authenticated vulnerability scan")
print(workflow)
if re.search(r"(?m)^\s*\d+[.)]", workflow):
    print("PASS\n")
else:
    print("FAIL\n")
    exit_code = 1

print("=== web_search ===")
if not os.environ.get("TAVILY_API_KEY"):
    print("SKIPPED: TAVILY_API_KEY not set\n")
else:
    print(tools.web_search("Qualys VMDR documentation 2025"))

sys.exit(exit_code)
