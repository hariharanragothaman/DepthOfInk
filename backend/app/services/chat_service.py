"""Character-mode chat: RAG context + stay-in-character prompt + citations."""
from __future__ import annotations

from openai import OpenAI

from app.config import settings
from app.models.schemas import CharacterInfo, ChatMessage
from app.services.rag_service import retrieve

SYSTEM_PREFIX = """You are roleplaying as "{name}" from the story. Stay in character. Use the following context from the book to keep your voice and facts accurate. If the context does not contain relevant information, stay in character but do not invent plot details. You may say you don't recall or keep the reply short and in character.
"""

CONTEXT_BLOCK = """
Relevant passages from the book (use these for tone and facts; cite by [Page X] when you rely on them):
---
{context}
---
"""


def build_system_prompt(character: CharacterInfo, context_str: str) -> str:
    parts = [SYSTEM_PREFIX.format(name=character.name)]
    if character.description:
        parts.append(f"About you: {character.description}\n")
    if character.example_quotes:
        parts.append("Example lines that sound like you:\n" + "\n".join(f'- "{q}"' for q in character.example_quotes))
    if context_str:
        parts.append(CONTEXT_BLOCK.format(context=context_str))
    parts.append('\nRespond only as this character. Do not break character or mention you are an AI.')
    return "\n".join(parts)


def format_context(citations: list[dict]) -> str:
    return "\n\n".join(
        f"[Page {c.get('page', '?')}]\n{c.get('text', '')}"
        for c in citations
    )


def chat(
    character: CharacterInfo,
    book_id: str,
    user_message: str,
    history: list[ChatMessage],
) -> tuple[str, list[dict]]:
    """One non-streaming turn: return (assistant_content, citations_used)."""
    citations = retrieve(book_id, user_message, top_k=settings.top_k_retrieve)
    context_str = format_context(citations)

    messages = [
        {"role": "system", "content": build_system_prompt(character, context_str)},
    ]
    for m in history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        temperature=0.7,
    )
    content = (response.choices[0].message.content or "").strip()
    return content, citations


def chat_stream(
    character: CharacterInfo,
    book_id: str,
    user_message: str,
    history: list[ChatMessage],
):
    """Stream assistant reply and yield (content_delta, citations_at_end)."""
    citations = retrieve(book_id, user_message, top_k=settings.top_k_retrieve)
    context_str = format_context(citations)

    messages = [
        {"role": "system", "content": build_system_prompt(character, context_str)},
    ]
    for m in history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    stream = client.chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    yield None  # signal end; caller can attach citations
