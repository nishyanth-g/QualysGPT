"""Command-line Q&A over Qualys notes: retrieve context, ask Claude."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "retrieval"))

import anthropic
from dotenv import load_dotenv
from retriever import Retriever

load_dotenv()

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = "You are QualysGPT. Answer only from the provided context. End with: Source: {cert_name} / {h1}"

retriever = Retriever()
client = anthropic.Anthropic()

while True:
    question = input("\nAsk a Qualys question (or 'exit'): ").strip()
    if question.lower() == "exit":
        break
    if not question:
        continue

    results = retriever.search(question, top_k=5)
    context = retriever.format_context(results)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}],
    )
    answer = next((b.text for b in response.content if b.type == "text"), "")
    print(f"\n{answer}")
