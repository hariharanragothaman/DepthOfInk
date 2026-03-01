"""RAG: embed chunks, store in Chroma, retrieve with metadata, rerank."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.llm_provider import get_provider
from app.services.pdf_service import TextChunk

logger = logging.getLogger(__name__)


def get_chroma_client(book_id: str):
    """Persistent Chroma client for one book's collection."""
    book_path = settings.chroma_dir / book_id
    book_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(book_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_embedding(text: str) -> list[float]:
    return get_provider().embed(text, model=settings.embedding_model)


def create_collection(book_id: str, chunks: list[TextChunk]) -> None:
    """Create Chroma collection and add chunk embeddings with chapter metadata."""
    client = get_chroma_client(book_id)
    coll = client.get_or_create_collection(
        name="chunks",
        metadata={"description": "Book chunks for RAG"},
    )
    if coll.count() > 0:
        return

    ids = [f"c_{c.chunk_index}" for c in chunks]
    texts = [c.text for c in chunks]
    metadatas = [
        {
            "page": c.page,
            "chunk_index": c.chunk_index,
            "chapter": c.chapter if c.chapter is not None else -1,
            "chapter_title": c.chapter_title or "",
        }
        for c in chunks
    ]

    embeddings = get_provider().embed_batch(texts, model=settings.embedding_model)

    coll.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def retrieve(
    book_id: str,
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return top-k relevant chunks with text, page, chapter, and score."""
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
            entry: dict[str, Any] = {
                "text": doc,
                "page": meta.get("page", 0),
                "score": round(score, 4),
            }
            ch = meta.get("chapter", -1)
            if ch is not None and ch != -1:
                entry["chapter"] = ch
                entry["chapter_title"] = meta.get("chapter_title", "")
            out.append(entry)
    return out


RERANK_PROMPT = """Given a user query and a set of text passages, rank the passages by relevance to the query.

Query: {query}

Passages:
{passages}

Return ONLY a JSON array of the indices (0-based) of the {final_k} most relevant passages, ordered from most to least relevant.
Example: [2, 0, 4, 1, 3]"""


def _rerank_with_llm(
    query: str,
    passages: list[dict[str, Any]],
    final_k: int,
) -> list[dict[str, Any]]:
    """Call LLM to rerank passages. Returns the top final_k passages in relevance order."""
    passages_text = "\n\n".join(
        f"[{i}] (Page {p.get('page', '?')}): {p['text'][:500]}"
        for i, p in enumerate(passages)
    )
    prompt = RERANK_PROMPT.format(
        query=query,
        passages=passages_text,
        final_k=min(final_k, len(passages)),
    )
    messages = [
        {"role": "system", "content": "You are a passage relevance ranker. Return only a JSON array of indices."},
        {"role": "user", "content": prompt},
    ]
    response = get_provider().chat(messages, model=settings.chat_model, temperature=0.0)
    try:
        start = response.index("[")
        end = response.rindex("]") + 1
        indices = json.loads(response[start:end])
        reranked = []
        for idx in indices[:final_k]:
            if isinstance(idx, int) and 0 <= idx < len(passages):
                reranked.append(passages[idx])
        return reranked if reranked else passages[:final_k]
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Reranking parse failed, falling back to original order: %s", e)
        return passages[:final_k]


def retrieve_and_rerank(
    book_id: str,
    query: str,
    initial_k: int | None = None,
    final_k: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve broad candidates then rerank with LLM for higher precision."""
    ik = initial_k or settings.rerank_initial_k
    fk = final_k or settings.rerank_final_k

    candidates = retrieve(book_id, query, top_k=ik)
    if len(candidates) <= fk:
        return candidates

    try:
        return _rerank_with_llm(query, candidates, fk)
    except Exception as e:
        logger.warning("Reranking failed, returning original top-K: %s", e)
        return candidates[:fk]
