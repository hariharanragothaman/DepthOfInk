"""Chat endpoint with streaming and citations."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from app.models.schemas import ChatMessage, ChatRequest
from app.services.book_store import get_character
from app.services.chat_service import chat_stream

router = APIRouter(prefix="/chat", tags=["chat"])


def _stream_chat(book_id: str, character_id: str, message: str, history: list[dict]):
    character = get_character(book_id, character_id)
    if not character:
        yield json.dumps({"type": "error", "content": "Character not found"}) + "\n"
        return
    hist = [ChatMessage(role=m["role"], content=m["content"], citations=m.get("citations", [])) for m in history]
    citations_used = []
    try:
        for delta in chat_stream(character, book_id, message, hist):
            if delta is None:
                break
            yield json.dumps({"type": "content", "content": delta}) + "\n"
        # After stream ends we need to get citations from the last retrieve call.
        # For simplicity we do a non-streaming pass to get citations, or we could
        # refactor chat_stream to return citations. Here we'll send a final citation payload
        # by running retrieve again (cheap) and sending one more event.
        from app.services.rag_service import retrieve
        citations_used = retrieve(book_id, message, top_k=5)
        yield json.dumps({"type": "citations", "citations": citations_used}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"


@router.post("/stream")
def chat_stream_endpoint(req: ChatRequest):
    """Stream assistant reply as newline-delimited JSON: { type, content?, citations? }."""
    character = get_character(req.book_id, req.character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return StreamingResponse(
        _stream_chat(
            req.book_id,
            req.character_id,
            req.message,
            [m.model_dump() for m in req.history],
        ),
        media_type="application/x-ndjson",
    )


@router.post("/message")
def chat_message(req: ChatRequest):
    """Non-streaming single message (for simpler clients)."""
    from app.services.chat_service import chat
    character = get_character(req.book_id, req.character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    hist = [ChatMessage(role=m["role"], content=m["content"], citations=m.get("citations", [])) for m in req.history]
    content, citations = chat(character, req.book_id, req.message, hist)
    return {"content": content, "citations": citations}
