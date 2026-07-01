"""Verify Qdrant retrieval quality after ingestion. Exits 1 on failure."""

import sys

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

COLLECTION = "qualys_notes"
EMBED_MODEL = "text-embedding-3-small"
SCORE_THRESHOLD = 0.5
QUERIES = [
    "What is a QID?",
    "How do I create an asset group?",
    "What is TruRisk?",
]


def main():
    load_dotenv()
    openai_client = OpenAI()
    qdrant = QdrantClient(url="http://localhost:6333")

    all_ok = True
    for query in QUERIES:
        print(f"\nQuery: {query}")
        vector = openai_client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
        results = qdrant.query_points(collection_name=COLLECTION, query=vector, limit=5).points

        if not results or max(r.score for r in results) <= SCORE_THRESHOLD:
            all_ok = False

        if not results:
            print("  No results.")
            continue

        for r in results:
            p = r.payload
            print(f"  score={r.score:.3f} cert={p['cert_name']} h1={p['h1']} h2={p['h2']}")
            print(f"    {p['text'][:150]}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
