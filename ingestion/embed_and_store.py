"""Chunk parsed/scraped blocks, embed them, and upsert into Qdrant."""

import argparse
import re
import time
import uuid
from pathlib import Path

import parse_md
import scrape_urls
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION = "qualys_notes"
VECTOR_SIZE = 1536
MAX_TOKENS = 800
EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 20
UPSERT_BATCH = 100


def last_two_sentences(text: str) -> str:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    return " ".join(sentences[-2:])


def group_blocks(blocks: list[dict]) -> dict:
    groups = {}
    for b in blocks:
        key = (b["cert_name"], b["source_file"], b["h1"], b["h2"])
        groups.setdefault(key, {"source_type": b["source_type"], "texts": []})
        groups[key]["texts"].append(b["text"])
    return groups


def chunk_group(h1: str, h2: str, full_text: str, enc) -> list[str]:
    if len(enc.encode(full_text)) <= MAX_TOKENS:
        raw_chunks = [full_text]
    else:
        paragraphs = [p for p in full_text.split("\n") if p.strip()]
        raw_chunks = []
        current = []
        for para in paragraphs:
            candidate = current + [para]
            if current and len(enc.encode("\n".join(candidate))) > MAX_TOKENS:
                raw_chunks.append("\n".join(current))
                current = [para]
            else:
                current = candidate
        if current:
            raw_chunks.append("\n".join(current))

    prefix = f"Module: {h1} | Topic: {h2} — "
    final_chunks = []
    prev_raw = None
    for raw in raw_chunks:
        body = f"{last_two_sentences(prev_raw)}\n{raw}" if prev_raw else raw
        final_chunks.append(prefix + body)
        prev_raw = raw
    return final_chunks


def build_chunks(blocks: list[dict], enc) -> list[dict]:
    groups = group_blocks(blocks)
    chunks = []
    current_file = None
    idx = 0
    for (cert_name, source_file, h1, h2), data in groups.items():
        if source_file != current_file:
            current_file = source_file
            idx = 0
        full_text = "\n".join(data["texts"])
        for chunk_text in chunk_group(h1, h2, full_text, enc):
            chunks.append({
                "cert_name": cert_name,
                "source_type": data["source_type"],
                "source_file": source_file,
                "h1": h1,
                "h2": h2,
                "chunk_index": idx,
                "text": chunk_text,
            })
            idx += 1
    return chunks


def ensure_collection(qdrant: QdrantClient, reset: bool):
    exists = qdrant.collection_exists(COLLECTION)
    if reset and exists:
        print(f"WARNING: --reset passed, deleting existing '{COLLECTION}' collection")
        qdrant.delete_collection(COLLECTION)
        exists = False
    if not exists:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        vectors.extend(d.embedding for d in resp.data)
        print(f"Embedded {min(i + EMBED_BATCH, len(texts))}/{len(texts)}")
    return vectors


def upsert_chunks(qdrant: QdrantClient, chunks: list[dict], vectors: list[list[float]]):
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=vector, payload=chunk)
        for chunk, vector in zip(chunks, vectors)
    ]
    for i in range(0, len(points), UPSERT_BATCH):
        batch = points[i:i + UPSERT_BATCH]
        qdrant.upsert(collection_name=COLLECTION, points=batch)
        print(f"Upserted {min(i + UPSERT_BATCH, len(points))}/{len(points)}")


def main(cert: str | None = None, reset: bool = False):
    load_dotenv()
    start = time.perf_counter()

    blocks = parse_md.main(cert) + scrape_urls.main(cert)
    enc = tiktoken.get_encoding("cl100k_base")
    chunks = build_chunks(blocks, enc)

    qdrant = QdrantClient(url="http://localhost:6333")
    ensure_collection(qdrant, reset)

    openai_client = OpenAI()
    vectors = embed_texts(openai_client, [c["text"] for c in chunks])
    upsert_chunks(qdrant, chunks, vectors)

    per_cert = {}
    for c in chunks:
        per_cert[c["cert_name"]] = per_cert.get(c["cert_name"], 0) + 1

    print("\nChunks per cert:")
    for cert_name, count in per_cert.items():
        print(f"{cert_name}: {count}")

    total_points = qdrant.get_collection(COLLECTION).points_count
    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Total Qdrant points: {total_points}")
    print(f"Time taken: {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert", help="Process only this cert (e.g. VMDR)")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate the collection")
    args = parser.parse_args()
    main(args.cert, args.reset)
