"""RAG: embed chunks, store in Chroma, retrieve with metadata."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from app.config import settings
from app.services.pdf_service import TextChunk


def get_chroma_client(book_id: str):
    """Persistent Chroma client for one book's collection."""
    book_path = settings.chroma_dir / book_id
    book_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(book_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_embedding(text: str) -> list[float]:
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    r = client.embeddings.create(
        model=settings.embedding_model,
        input=text[:8000],
    )
    return r.data[0].embedding


def create_collection(book_id: str, chunks: list[TextChunk]) -> None:
    """Create Chroma collection and add chunk embeddings."""
    client = get_chroma_client(book_id)
    coll = client.get_or_create_collection(
        name="chunks",
        metadata={"description": "Book chunks for RAG"},
    )
    if coll.count() > 0:
        return

    ids = [f"c_{c.chunk_index}" for c in chunks]
    texts = [c.text for c in chunks]
    metadatas = [{"page": c.page, "chunk_index": c.chunk_index} for c in chunks]

    # Batch embed (OpenAI accepts multiple inputs per call)
    embeddings: list[list[float]] = []
    batch_size = 50
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        r = client.embeddings.create(model=settings.embedding_model, input=batch)
        batch_embeddings = [d.embedding for d in r.data]
        embeddings.extend(batch_embeddings)

    coll.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def retrieve(
    book_id: str,
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return top-k relevant chunks with text, page, and score."""
    k = top_k or settings.top_k_retrieve
    client = get_chroma_client(book_id)
    coll = client.get_collection(name="chunks")
    q_emb = get_embedding(query)
    results = coll.query(
        query_embeddings=[q_emb],
        n_results=min(k, coll.count()),
        include=["documents", "metadatas", "distances"],
    )
    out: list[dict[str, Any]] = []
    docs = results["documents"][0] or []
    metadatas = results["metadatas"][0] or []
    distances = results["distances"][0] or []
    for doc, meta, dist in zip(docs, metadatas, distances):
        score = 1.0 - (dist / 2.0) if dist is not None else 1.0
        if score >= settings.min_relevance_score:
            out.append({
                "text": doc,
                "page": meta.get("page", 0),
                "score": round(score, 4),
            })
    return out
