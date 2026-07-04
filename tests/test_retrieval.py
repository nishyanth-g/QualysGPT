"""Verify Qdrant retrieval quality after ingestion. Run via: pytest tests/test_retrieval.py"""

import sys

import pytest
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

COLLECTION = "qualys_notes"
EMBED_MODEL = "text-embedding-3-small"
SCORE_THRESHOLD = 0.5

load_dotenv()
openai_client = OpenAI()
qdrant = QdrantClient(url="http://localhost:6333")


def _check_query(query: str):
    print(f"\nQuery: {query}")
    vector = openai_client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
    results = qdrant.query_points(collection_name=COLLECTION, query=vector, limit=5).points

    assert results, "No results returned"
    for r in results:
        p = r.payload
        print(f"  score={r.score:.3f} cert={p['cert_name']} h1={p['h1']} h2={p['h2']}")
        print(f"    {p['text'][:150]}")

    best_score = max(r.score for r in results)
    assert best_score > SCORE_THRESHOLD, f"best score {best_score:.3f} did not clear {SCORE_THRESHOLD}"


@pytest.mark.xfail(reason="known retrieval gap: broad 'What is a QID' query ranks TruRisk/QDS chunk above KnowledgeBase definition — documented in README known issues")
def test_what_is_a_qid():
    _check_query("What is a QID?")


def test_create_asset_group():
    _check_query("How do I create an asset group?")


def test_what_is_trurisk():
    _check_query("What is TruRisk?")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
