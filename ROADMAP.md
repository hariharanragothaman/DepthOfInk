# DepthOfInk — Roadmap

## Phase 1: MVP ✅

- [x] PDF ingestion (text extraction + chunking)
- [x] Character detection (prompt-based extraction)
- [x] RAG (embeddings + Chroma, retrieval + citations)
- [x] Chat UI (Next.js: upload, character picker, streamed chat)
- [x] Character-mode prompt + constraints + citations back to PDF
- [x] Multi-provider LLM support (OpenAI / Bedrock / Ollama)

---

## Phase 2: Solid Prototype ✅

- [x] Chapter-aware PDF parsing with boundary detection
- [x] Two-pass character extraction (broad recall → ranked merge, up to 20 characters)
- [x] Per-character conversation memory with automatic summarization
- [x] LLM-based reranking for higher-precision retrieval
- [x] Multi-character group chat
- [x] Character relationship extraction and visual graph
- [x] Background processing with polling UI

---

## Phase 3: Production Hardening (In Progress)

- [x] Per-endpoint rate limiting (slowapi)
- [x] File validation and size limits (50 MB, PDF magic bytes)
- [x] CORS lockdown (configurable origins)
- [x] Input sanitization (message length limits)
- [x] Delete book with full cleanup (PDF, embeddings, conversations)
- [x] Retry processing for failed books
- [x] Structured JSON logging with request ID correlation
- [x] Health check probes (ChromaDB + filesystem writability)
- [x] Concurrent upload limiting (asyncio semaphore)
- [x] CI pipeline (GitHub Actions: tests + TypeScript + build)
- [x] AWS deployment (Terraform: ECS Fargate + S3/CloudFront + EFS)
- [ ] Staged progress indicator during PDF processing
- [ ] Show page count and text length after upload
- [ ] Mobile-friendly upload improvements
- [ ] Export conversations as text/JSON
- [ ] Update .env.example with all new settings
- [ ] Evaluation harness for character fidelity and citation accuracy

---

## Stretch Goals

- [ ] Voice / TTS for character dialogue
- [ ] Scene mode ("everyone in this chapter")
- [ ] Public gallery of sample books (public domain)
- [ ] Per-user API key management and quotas
- [ ] Database backend (replace JSON files with SQLite/Postgres)
- [ ] Optional auth for "my books" and sharing
