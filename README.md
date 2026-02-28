# DepthOfInk

**Chat with characters from your storybook PDFs.** Upload a narrative PDF, get auto-detected characters, and talk to them with responses grounded in the book and cited back to the source.

---

## Quick start

### 1. Backend (Python)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # edit .env and set OPENAI_API_KEY=sk-...
```

Then start the server (venv must be active):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Tip:** If you see `uvicorn: command not found`, make sure you ran `source .venv/bin/activate` first. You can verify with `which uvicorn` -- it should point to `.venv/bin/uvicorn`.

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # optional; defaults to http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), upload a story PDF, then pick a character and chat.

### 3. Environment

- **Backend** `backend/.env`: set `LLM_PROVIDER` and provider-specific keys. See `.env.example` for all options.
- **Frontend** `frontend/.env.local`: set `NEXT_PUBLIC_API_URL` if the API is not at `http://localhost:8000`.

---

## LLM Provider Configuration

The backend supports multiple LLM providers via the `LLM_PROVIDER` env var. Set it in `backend/.env`:

### OpenAI (default)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

### AWS Bedrock

```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
CHAT_MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
```

Requires AWS credentials configured via `~/.aws/credentials`, env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), or an IAM role (on EC2/ECS).

### Ollama (local, free)

```env
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=unused
CHAT_MODEL=llama3
EMBEDDING_MODEL=nomic-embed-text
```

Requires [Ollama](https://ollama.com) running locally with the models pulled.

---

## What's in the MVP

- **PDF ingestion**: Text extraction (PyMuPDF with pdfplumber fallback), chunking with overlap.
- **Character detection**: Prompt-based extraction of 2-6 main characters and short profiles.
- **RAG**: Embeddings and Chroma for retrieval; citations with page numbers.
- **Chat**: Character-mode system prompt, retrieval-augmented replies, streaming, citations in the UI.
- **UI**: Next.js home (upload + book list), book page with character tabs and chat.
- **Multi-provider**: Swap between OpenAI, AWS Bedrock, or Ollama with a single env var.

---

## Project layout

```
DepthOfInk/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # books, characters, chat
│   │   ├── models/         # Pydantic schemas
│   │   ├── services/       # pdf, characters, rag, chat, book_store, llm_provider
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/              # pytest suite (61 tests)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                # Next.js app router
│   ├── lib/api.ts          # API client
│   └── package.json
├── infra/                  # Terraform (AWS ECS Fargate deployment)
├── ROADMAP.md              # Phases 2+
└── README.md
```

---

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for Phase 2 (better parsing, auto character profiles, memory, UI polish, eval) and stretch goals.

---

## License

See [LICENSE](./LICENSE).
