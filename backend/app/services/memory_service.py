"""Memory summarization service."""
from __future__ import annotations

from app.config import settings
from app.services.conversation_store import (
    get_memory_summary,
    load_messages,
    save_messages,
    update_memory_summary,
)
from app.services.llm_provider import get_provider

SUMMARIZE_PROMPT = """You are a summarizer. Given a conversation between a user and an AI character roleplaying from a book, produce a concise summary that captures:
- Key topics discussed
- Important facts or preferences the user mentioned
- The tone and direction of the conversation

Keep the summary under 300 words. Write in third person. This summary will be used as context for future turns."""


def summarize_if_needed(
    book_id: str,
    character_id: str,
    new_messages: list[dict],
    threshold: int = 10,
) -> None:
    """Load existing messages, append new_messages, save. If total >= threshold, summarize and save summary."""
    existing = load_messages(book_id, character_id)
    all_messages = existing + new_messages
    save_messages(book_id, character_id, new_messages)

    if len(all_messages) >= threshold:
        # Build conversation text for the LLM
        conv_text_parts = []
        for m in all_messages:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            conv_text_parts.append(f"{role}: {content}")

        conv_text = "\n".join(conv_text_parts)
        messages = [
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": f"Summarize this conversation:\n\n{conv_text}"},
        ]
        summary = get_provider().chat(
            messages, model=settings.chat_model, temperature=0.3
        )
        update_memory_summary(book_id, character_id, summary.strip())


def get_memory_context(book_id: str, character_id: str) -> str | None:
    """Return the memory summary if it exists and is non-empty, else None."""
    summary = get_memory_summary(book_id, character_id)
    if summary and summary.strip():
        return summary.strip()
    return None
