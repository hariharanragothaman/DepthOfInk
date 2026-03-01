"""Character-mode chat: RAG context + stay-in-character prompt + citations + memory."""
from __future__ import annotations

from app.config import settings
from app.models.schemas import CharacterInfo, ChatMessage
from app.services.llm_provider import get_provider
from app.services.rag_service import retrieve, retrieve_and_rerank
from app.services.memory_service import get_memory_context, summarize_if_needed

SYSTEM_PREFIX = """You are roleplaying as "{name}" from the story. Stay in character. Use the following context from the book to keep your voice and facts accurate. If the context does not contain relevant information, stay in character but do not invent plot details. You may say you don't recall or keep the reply short and in character.
"""

CONTEXT_BLOCK = """
Relevant passages from the book (use these for tone and facts; cite by [Page X] when you rely on them):
---
{context}
---
"""

MEMORY_BLOCK = """
What you remember from previous conversations:
{memory}
"""


def build_system_prompt(
    character: CharacterInfo,
    context_str: str,
    memory_summary: str | None = None,
) -> str:
    parts = [SYSTEM_PREFIX.format(name=character.name)]
    if character.description:
        parts.append(f"About you: {character.description}\n")
    if character.example_quotes:
        parts.append("Example lines that sound like you:\n" + "\n".join(f'- "{q}"' for q in character.example_quotes))
    if memory_summary:
        parts.append(MEMORY_BLOCK.format(memory=memory_summary))
    if context_str:
        parts.append(CONTEXT_BLOCK.format(context=context_str))
    parts.append('\nRespond only as this character. Do not break character or mention you are an AI.')
    return "\n".join(parts)


def format_context(citations: list[dict]) -> str:
    parts = []
    for c in citations:
        label = f"[Page {c.get('page', '?')}"
        if c.get("chapter"):
            label += f", Chapter {c['chapter']}"
        label += "]"
        parts.append(f"{label}\n{c.get('text', '')}")
    return "\n\n".join(parts)


def _get_citations(book_id: str, query: str) -> list[dict]:
    if settings.rerank_enabled:
        return retrieve_and_rerank(book_id, query)
    return retrieve(book_id, query, top_k=settings.top_k_retrieve)


def chat(
    character: CharacterInfo,
    book_id: str,
    user_message: str,
    history: list[ChatMessage],
) -> tuple[str, list[dict]]:
    """One non-streaming turn: return (assistant_content, citations_used)."""
    citations = _get_citations(book_id, user_message)
    context_str = format_context(citations)
    memory = get_memory_context(book_id, character.id)

    messages = [
        {"role": "system", "content": build_system_prompt(character, context_str, memory)},
    ]
    for m in history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})

    content = get_provider().chat(messages, model=settings.chat_model, temperature=0.7)

    summarize_if_needed(book_id, character.id, [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": content},
    ])

    return content, citations


def chat_stream(
    character: CharacterInfo,
    book_id: str,
    user_message: str,
    history: list[ChatMessage],
):
    """Stream assistant reply and yield content deltas. Saves memory after completion."""
    citations = _get_citations(book_id, user_message)
    context_str = format_context(citations)
    memory = get_memory_context(book_id, character.id)

    messages = [
        {"role": "system", "content": build_system_prompt(character, context_str, memory)},
    ]
    for m in history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})

    collected_content: list[str] = []
    for delta in get_provider().chat_stream(messages, model=settings.chat_model, temperature=0.7):
        if delta is not None:
            collected_content.append(delta)
        yield delta

    full_reply = "".join(collected_content)
    summarize_if_needed(book_id, character.id, [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": full_reply},
    ])
