"""Chat endpoints with streaming, citations, group chat, and memory."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import json

from app.config import settings
from app.models.schemas import ChatMessage, ChatRequest, GroupChatRequest
from app.services.book_store import get_character
from app.services.chat_service import chat_stream
from app.services import conversation_store

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_limiter():
    from app.rate_limit import limiter
    return limiter


def _stream_chat(book_id: str, character_id: str, message: str, history: list[dict]):
    character = get_character(book_id, character_id)
    if not character:
        yield json.dumps({"type": "error", "content": "Character not found"}) + "\n"
        return
    hist = [ChatMessage(role=m["role"], content=m["content"], citations=m.get("citations", [])) for m in history]
    try:
        for delta in chat_stream(character, book_id, message, hist):
            if delta is None:
                break
            yield json.dumps({"type": "content", "content": delta}) + "\n"
        from app.services.rag_service import retrieve
        citations_used = retrieve(book_id, message, top_k=5)
        yield json.dumps({"type": "citations", "citations": citations_used}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"


@router.post("/stream")
@_get_limiter().limit(settings.rate_limit_chat)
def chat_stream_endpoint(request: Request, req: ChatRequest):
    """Stream assistant reply as newline-delimited JSON."""
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
@_get_limiter().limit(settings.rate_limit_chat)
def chat_message(request: Request, req: ChatRequest):
    """Non-streaming single message."""
    from app.services.chat_service import chat
    character = get_character(req.book_id, req.character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    hist = [ChatMessage(role=m["role"], content=m["content"], citations=m.get("citations", [])) for m in req.history]
    content, citations = chat(character, req.book_id, req.message, hist)
    return {"content": content, "citations": citations}


# --- Conversation History / Memory ---

@router.get("/history/{book_id}/{character_id}")
@_get_limiter().limit(settings.rate_limit_default)
def get_chat_history(request: Request, book_id: str, character_id: str):
    """Load past conversation messages."""
    messages = conversation_store.load_messages(book_id, character_id)
    summary = conversation_store.get_memory_summary(book_id, character_id)
    return {"messages": messages, "memory_summary": summary}


@router.delete("/history/{book_id}/{character_id}")
@_get_limiter().limit(settings.rate_limit_default)
def clear_chat_history(request: Request, book_id: str, character_id: str):
    """Clear conversation memory for a character."""
    conversation_store.clear_conversation(book_id, character_id)
    return {"status": "cleared"}


# --- Group Chat ---

def _stream_group_chat(book_id: str, character_ids: list[str], message: str, history: list[dict]):
    from app.services.group_chat_service import group_chat_stream
    try:
        for event in group_chat_stream(book_id, character_ids, message, history):
            yield json.dumps(event) + "\n"
    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"


@router.post("/group/stream")
@_get_limiter().limit(settings.rate_limit_chat)
def group_chat_stream_endpoint(request: Request, req: GroupChatRequest):
    """Stream group chat replies as NDJSON."""
    if not req.character_ids:
        raise HTTPException(status_code=400, detail="At least one character required")
    return StreamingResponse(
        _stream_group_chat(
            req.book_id,
            req.character_ids,
            req.message,
            [m.model_dump() for m in req.history],
        ),
        media_type="application/x-ndjson",
    )


@router.post("/group/message")
@_get_limiter().limit(settings.rate_limit_chat)
def group_chat_message(request: Request, req: GroupChatRequest):
    """Non-streaming group chat."""
    from app.services.group_chat_service import group_chat
    if not req.character_ids:
        raise HTTPException(status_code=400, detail="At least one character required")
    history = [m.model_dump() for m in req.history]
    results = group_chat(req.book_id, req.character_ids, req.message, history)
    return {"replies": results}
