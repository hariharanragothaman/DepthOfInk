# DepthOfInk — Roadmap

## Phase 1: MVP ✅

- [x] PDF ingestion (text extraction + chunking)
- [x] Character detection (prompt-based extraction)
- [x] RAG (embeddings + Chroma, retrieval + citations)
- [x] Chat UI (Next.js: upload, character picker, streamed chat)
- [x] Character-mode prompt + constraints + citations back to PDF

**Result:** Working demo. Characters may drift; works best on clean PDFs.

---

## Phase 2: Solid prototype (~40–80h)

Goal: Better character consistency, memory per character, scene grounding, citations, and guardrails.

| Area | Tasks | Est. |
|------|--------|------|
| **PDF parsing** | Layout fixes, chapter boundaries, cleanup | 6–12h |
| **Characters** | Auto character list + profiles (aliases, relationships, example quotes) | 8–16h |
| **Retrieval** | Chapter-aware retrieval, reranking, quote snippets | 6–12h |
| **Memory** | Per-character memories + conversation summary | 6–12h |
| **UI** | Character selection polish, “scene mode”, export chat | 6–16h |
| **Eval** | Basic harness (hallucination / citation checks) | 2–6h |

**Result:** Shareable with friends; mostly holds up.

---

## Stretch

- Multi-character group chats
- Scene mode (e.g. “everyone in this chapter”)
- Voice / TTS for character lines
- Public gallery of sample books (with permission)

---

## Technical debt / later

- Replace in-memory book store with SQLite or Postgres
- Optional auth for “my books” and sharing
- Rate limiting and guardrails on generated content
