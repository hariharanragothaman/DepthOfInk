# DepthOfInk

**Chat with characters from your storybook PDFs.** Upload a narrative PDF, get auto-detected characters, and talk to them with responses grounded in the book and cited back to the source.

---

## Quick start

### 1. Backend (Python)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # set OPENAI_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

From the project root you can run:

```bash
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # optional; defaults to http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), upload a story PDF, then pick a character and chat.

### 3. Environment

- **Backend** `backend/.env`: set `OPENAI_API_KEY`. Optionally `OPENAI_BASE_URL` for another API, and override paths/models (see `.env.example`).
- **Frontend** `frontend/.env.local`: set `NEXT_PUBLIC_API_URL` if the API is not at `http://localhost:8000`.

---

## What’s in the MVP

- **PDF ingestion**: Text extraction (PyMuPDF → pdfplumber fallback), chunking with overlap.
- **Character detection**: Prompt-based extraction of 2–6 main characters and short profiles.
- **RAG**: Embeddings (OpenAI) and Chroma for retrieval; citations with page numbers.
- **Chat**: Character-mode system prompt, retrieval-augmented replies, streaming, citations in the UI.
- **UI**: Next.js home (upload + book list), book page with character tabs and chat.

---

## Project layout

```
DepthOfInk/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # books, characters, chat
│   │   ├── models/         # Pydantic schemas
│   │   ├── services/       # pdf, characters, rag, chat, book_store
│   │   ├── config.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                # Next.js app router
│   ├── lib/api.ts          # API client
│   └── package.json
├── ROADMAP.md              # Phases 2+
└── README.md
```

---

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for Phase 2 (better parsing, auto character profiles, memory, UI polish, eval) and stretch goals.

---

## License

See [LICENSE](./LICENSE).
