"""Thin retrieval wrapper over Qdrant + OpenAI embeddings."""

import socket
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

load_dotenv()

COLLECTION = "qualys_notes"
EMBED_MODEL = "text-embedding-3-small"
QDRANT_URL = "http://localhost:6333"


class Retriever:
    def __init__(self):
        self.openai_client = OpenAI()
        self.qdrant = QdrantClient(url=QDRANT_URL, timeout=3, check_compatibility=False)

    def embed_query(self, query: str) -> list[float]:
        return self.openai_client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding

    def _qdrant_reachable(self, timeout: float = 1.0) -> bool:
        parsed = urlparse(QDRANT_URL)
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=timeout):
                return True
        except OSError:
            return False

    def search(self, query: str, cert_filter: str | None = None, top_k: int = 5) -> list[dict]:
        if not self._qdrant_reachable():
            raise ConnectionRefusedError(f"Qdrant is not reachable at {QDRANT_URL}")

        query_filter = None
        if cert_filter:
            query_filter = Filter(must=[FieldCondition(key="cert_name", match=MatchValue(value=cert_filter))])

        results = self.qdrant.query_points(
            collection_name=COLLECTION,
            query=self.embed_query(query),
            query_filter=query_filter,
            limit=top_k,
        ).points

        return [
            {
                "score": r.score,
                "cert_name": r.payload["cert_name"],
                "source_type": r.payload["source_type"],
                "h1": r.payload["h1"],
                "h2": r.payload["h2"],
                "text": r.payload["text"],
            }
            for r in results
        ]

    def format_context(self, results: list[dict]) -> str:
        return "\n---\n".join(
            f"[Source: {r['cert_name']} / {r['h1']} / {r['h2']}]\n{r['text']}"
            for r in results
        )

    def get_collection_info(self) -> dict:
        info = self.qdrant.get_collection(COLLECTION)
        return {"collection": COLLECTION, "point_count": info.points_count}
