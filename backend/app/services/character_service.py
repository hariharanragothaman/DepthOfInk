"""Character detection: multi-sample extraction and relationship graph from book text."""
from __future__ import annotations

import json
import logging
import re

from app.config import settings
from app.models.schemas import CharacterInfo, CharacterRelationship
from app.services.llm_provider import get_provider

logger = logging.getLogger(__name__)


SYSTEM_EXTRACT = """You are an expert at analyzing narrative text. Given excerpts from a story or book, list the main characters that a reader would want to "talk to" in a chat. Focus on named characters with dialogue or clear presence, not minor walk-ons. Return valid JSON only, no markdown or explanation."""

USER_EXTRACT = """From this book excerpt, list the main characters (aim for 6-12 for a full novel, fewer for shorter works). For each character provide:
- name: full or primary name (use their most common name in the story)
- description: 1-2 sentences about who they are in the story
- example_quotes: 1-3 short quotes that sound like them (optional but helpful)

Excerpt:
---
{text}
---

Return a JSON object with key "characters" and value an array of objects with keys: name, description, example_quotes (array of strings)."""

SYSTEM_MERGE = """You are an expert at analyzing characters from a novel. You will receive multiple lists of characters extracted from different parts of a book. Merge them into a single deduplicated list of the most important characters. Characters may appear under slightly different names (e.g. "Harry" vs "Harry Potter") -- unify them. Keep the best description and quotes from any source. Return valid JSON only."""

USER_MERGE = """Here are character lists extracted from different parts of the book. Merge them into one deduplicated list of the {max_chars} most important characters. Prefer characters with dialogue, plot significance, or strong presence.

{lists_json}

Return a JSON object with key "characters" and value an array of objects with keys: name, description, example_quotes (array of strings)."""

SYSTEM_RELATIONSHIPS = """You are an expert at analyzing character relationships in narrative fiction. Given a list of characters from a book and excerpts from the text, identify the key relationships between characters. Return valid JSON only, no markdown or explanation."""

USER_RELATIONSHIPS = """Given these characters from a book:
{characters_json}

And these excerpts from the story:
{text}

Identify the important relationships between characters. For each relationship provide:
- source: name of first character (must match a character name above exactly)
- target: name of second character (must match a character name above exactly)
- relationship: a short label (e.g. "best friends", "mother and son", "rivals", "mentor", "enemies", "classmates")
- description: 1 sentence describing the relationship

Return a JSON object with key "relationships" and value an array of objects with keys: source, target, relationship, description. Include only meaningful relationships, not every possible pair. Aim for 5-15 relationships."""


def _sample_excerpts(full_text: str, num_samples: int = 3, chars_per_sample: int = 6000) -> list[str]:
    """Sample excerpts from beginning, middle, and end of the text."""
    text_len = len(full_text)
    if text_len <= chars_per_sample * 2:
        return [full_text]

    excerpts = []
    if num_samples == 1:
        return [full_text[:chars_per_sample]]

    positions = [0]
    if num_samples >= 2:
        positions.append(text_len // 2 - chars_per_sample // 2)
    if num_samples >= 3:
        positions.append(max(0, text_len - chars_per_sample))
    for extra in range(3, num_samples):
        frac = extra / num_samples
        positions.append(int(text_len * frac) - chars_per_sample // 2)

    for pos in positions:
        start = max(0, pos)
        end = min(text_len, start + chars_per_sample)
        excerpts.append(full_text[start:end])

    return excerpts


def _extract_from_excerpt(text: str) -> list[dict]:
    """Extract characters from a single excerpt via LLM."""
    messages = [
        {"role": "system", "content": SYSTEM_EXTRACT},
        {"role": "user", "content": USER_EXTRACT.format(text=text)},
    ]
    raw = get_provider().chat(messages, model=settings.chat_model, temperature=0.2)
    raw = _strip_json_block(raw)
    data = json.loads(raw)
    chars = data.get("characters") or data
    if not isinstance(chars, list):
        chars = [chars]
    return chars


def _merge_character_lists(all_lists: list[list[dict]], max_chars: int = 12) -> list[dict]:
    """Use LLM to merge and deduplicate character lists from multiple excerpts."""
    if len(all_lists) == 1:
        return all_lists[0]

    lists_json = json.dumps(all_lists, indent=2)
    messages = [
        {"role": "system", "content": SYSTEM_MERGE},
        {"role": "user", "content": USER_MERGE.format(
            max_chars=max_chars,
            lists_json=lists_json,
        )},
    ]
    raw = get_provider().chat(messages, model=settings.chat_model, temperature=0.2)
    raw = _strip_json_block(raw)
    data = json.loads(raw)
    chars = data.get("characters") or data
    if not isinstance(chars, list):
        chars = [chars]
    return chars


def extract_characters(full_text: str, max_chars: int = 12) -> list[CharacterInfo]:
    """Extract characters by sampling multiple points in the book and merging results."""
    if not full_text.strip():
        return []

    text_len = len(full_text)
    if text_len < 15_000:
        num_samples = 1
    elif text_len < 50_000:
        num_samples = 2
    else:
        num_samples = 3

    excerpts = _sample_excerpts(full_text, num_samples=num_samples)

    all_lists: list[list[dict]] = []
    for excerpt in excerpts:
        try:
            chars = _extract_from_excerpt(excerpt)
            all_lists.append(chars)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Character extraction from excerpt failed: %s", e)
            continue

    if not all_lists:
        raise ValueError("All character extraction attempts failed")

    try:
        merged = _merge_character_lists(all_lists, max_chars=max_chars)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Merge failed, using first list: %s", e)
        merged = all_lists[0]

    out: list[CharacterInfo] = []
    for i, c in enumerate(merged[:max_chars]):
        name = (c.get("name") or c.get("title") or "Unknown").strip()
        if not name:
            continue
        desc = (c.get("description") or "").strip() or None
        quotes = c.get("example_quotes") or []
        if isinstance(quotes, str):
            quotes = [quotes]
        quotes = [str(q).strip() for q in quotes if q][:3]
        out.append(
            CharacterInfo(
                id=f"char_{i}_{_slug(name)}",
                name=name,
                description=desc,
                example_quotes=quotes,
            )
        )
    return out


def extract_relationships(
    full_text: str,
    characters: list[CharacterInfo],
) -> list[CharacterRelationship]:
    """Extract relationships between characters using LLM."""
    if len(characters) < 2:
        return []

    chars_json = json.dumps(
        [{"name": c.name, "description": c.description or ""} for c in characters],
        indent=2,
    )

    excerpts = _sample_excerpts(full_text, num_samples=3, chars_per_sample=4000)
    text = "\n\n---\n\n".join(excerpts)

    messages = [
        {"role": "system", "content": SYSTEM_RELATIONSHIPS},
        {"role": "user", "content": USER_RELATIONSHIPS.format(
            characters_json=chars_json,
            text=text,
        )},
    ]
    raw = get_provider().chat(messages, model=settings.chat_model, temperature=0.2)
    raw = _strip_json_block(raw)

    data = json.loads(raw)
    rels_raw = data.get("relationships") or data
    if not isinstance(rels_raw, list):
        rels_raw = [rels_raw]

    char_names = {c.name.lower() for c in characters}
    name_to_id = {c.name.lower(): c.id for c in characters}

    out: list[CharacterRelationship] = []
    for r in rels_raw:
        src = (r.get("source") or "").strip()
        tgt = (r.get("target") or "").strip()
        rel = (r.get("relationship") or "").strip()
        desc = (r.get("description") or "").strip()
        if not src or not tgt or not rel:
            continue
        src_id = name_to_id.get(src.lower())
        tgt_id = name_to_id.get(tgt.lower())
        if not src_id or not tgt_id or src_id == tgt_id:
            continue
        out.append(CharacterRelationship(
            source_id=src_id,
            target_id=tgt_id,
            source_name=src,
            target_name=tgt,
            relationship=rel,
            description=desc or None,
        ))
    return out


def _strip_json_block(s: str) -> str:
    s = s.strip()
    for start in ("```json", "```"):
        if s.startswith(start):
            s = s[len(start):].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return s


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unknown"
