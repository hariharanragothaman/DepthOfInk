"""Multi-character group chat orchestration."""
from __future__ import annotations

from typing import Generator

from app.config import settings
from app.models.schemas import CharacterInfo
from app.services.book_store import get_character
from app.services.chat_service import build_system_prompt, format_context
from app.services.llm_provider import get_provider
from app.services.rag_service import retrieve

OTHER_CHARS_BLOCK = """
Other characters in this conversation: {names}. You just heard them say: {prior_replies_this_round}. Respond naturally as yourself.
"""


def _build_group_system_prompt(
    character: CharacterInfo,
    context_str: str,
    other_names: list[str],
    prior_replies: list[str],
) -> str:
    base = build_system_prompt(character, context_str)
    names = ", ".join(other_names) if other_names else "none"
    prior_text = "\n".join(prior_replies) if prior_replies else "(no prior replies yet)"
    extra = OTHER_CHARS_BLOCK.format(names=names, prior_replies_this_round=prior_text)
    return base + "\n\n" + extra


def group_chat(
    book_id: str,
    character_ids: list[str],
    user_message: str,
    history: list[dict],
) -> list[dict]:
    """Retrieve context once, then for each character: build system prompt with other-character awareness, call LLM. Returns list of {character_id, character_name, content, citations}."""
    citations = retrieve(book_id, user_message, top_k=settings.top_k_retrieve)
    context_str = format_context(citations)

    prior_replies_this_round: list[str] = []
    results: list[dict] = []

    for character_id in character_ids:
        character = get_character(book_id, character_id)
        if not character:
            continue

        others = [cid for cid in character_ids if cid != character_id]
        other_names = []
        for cid in others:
            c = get_character(book_id, cid)
            if c:
                other_names.append(c.name)

        system_prompt = _build_group_system_prompt(
            character, context_str, other_names, prior_replies_this_round
        )

        full_messages = [{"role": "system", "content": system_prompt}]
        for m in history[-10:]:
            full_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        full_messages.append({"role": "user", "content": user_message})

        content = get_provider().chat(
            full_messages, model=settings.chat_model, temperature=0.7
        )
        prior_replies_this_round.append(content)
        results.append({
            "character_id": character_id,
            "character_name": character.name,
            "content": content,
            "citations": citations,
        })

    return results


def group_chat_stream(
    book_id: str,
    character_ids: list[str],
    user_message: str,
    history: list[dict],
) -> Generator[dict, None, None]:
    """Generator: character_start, content deltas, character_end per character; then citations, done."""
    citations = retrieve(book_id, user_message, top_k=settings.top_k_retrieve)
    context_str = format_context(citations)

    prior_replies_this_round: list[str] = []

    for character_id in character_ids:
        character = get_character(book_id, character_id)
        if not character:
            continue

        others = [cid for cid in character_ids if cid != character_id]
        other_names = []
        for cid in others:
            c = get_character(book_id, cid)
            if c:
                other_names.append(c.name)

        system_prompt = _build_group_system_prompt(
            character, context_str, other_names, prior_replies_this_round
        )

        full_messages = [{"role": "system", "content": system_prompt}]
        for m in history[-10:]:
            full_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        full_messages.append({"role": "user", "content": user_message})

        yield {"type": "character_start", "character_id": character_id, "character_name": character.name}

        collected = []
        for delta in get_provider().chat_stream(
            full_messages, model=settings.chat_model, temperature=0.7
        ):
            if delta is not None:
                collected.append(delta)
                yield {"type": "content", "content": delta}

        prior_replies_this_round.append("".join(collected))
        yield {"type": "character_end"}

    yield {"type": "citations", "citations": citations}
    yield {"type": "done"}
