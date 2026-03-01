"""Character detection: multi-sample extraction and relationship graph from book text.

Extraction uses a two-pass approach:
  Pass 1 (broad) -- sample excerpts across the book (chapter-aware when possible),
      extract *all* named characters from each excerpt in parallel.
  Pass 2 (rank & merge) -- LLM merges and ranks the union list, trimming to the
      configured max_characters limit.
"""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from app.config import settings
from app.models.schemas import CharacterInfo, CharacterRelationship
from app.services.llm_provider import get_provider

if TYPE_CHECKING:
    from app.services.pdf_service import Chapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_EXTRACT = (
    "You are an expert literary analyst. Given an excerpt from a book, "
    "identify every named character who speaks, acts, or is meaningfully "
    "referenced. Include protagonists, antagonists, supporting characters, "
    "and recurring side characters. Omit nameless background figures. "
    "Return valid JSON only, no markdown or explanation."
)

USER_EXTRACT = """List ALL named characters that appear in this excerpt. Do not limit yourself -- include every character who speaks, acts, or is meaningfully mentioned.

For each character provide:
- name: the character's most common name in the text
- description: 1-2 sentences about who they are
- example_quotes: 1-3 short quotes in their voice (empty array if none found)

Excerpt:
---
{text}
---

Return a JSON object with key "characters" containing an array of objects with keys: name, description, example_quotes."""

SYSTEM_MERGE = (
    "You are an expert at analyzing characters from a novel. You will receive "
    "multiple character lists extracted from different parts of a book. Merge "
    "them into a single deduplicated and ranked list. Characters may appear "
    "under slightly different names (e.g. 'Harry' vs 'Harry Potter') -- unify "
    "them under their most recognizable name. Keep the best description and "
    "quotes from any source. Return valid JSON only."
)

USER_MERGE = """Here are character lists extracted from different parts of the book:

{lists_json}

Merge and deduplicate these into a single ranked list of the top {max_chars} most important characters. Rank by:
1. Plot significance and screen time
2. Amount of dialogue
3. Emotional impact on the story
4. How interesting they would be to "chat with"

Include characters who only appear in one excerpt if they are plot-significant.

Return a JSON object with key "characters" containing an array of objects with keys: name, description, example_quotes (array of strings). Order from most to least important."""

SYSTEM_RELATIONSHIPS = (
    "You are an expert at analyzing character relationships in narrative "
    "fiction. Given a list of characters from a book and excerpts from the "
    "text, identify the key relationships between characters. Return valid "
    "JSON only, no markdown or explanation."
)

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


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def _compute_num_samples(text_len: int) -> int:
    """Scale sample count with book length for better character coverage."""
    if text_len < 15_000:
        return 1
    if text_len < 50_000:
        return 3
    if text_len < 100_000:
        return 5
    if text_len < 500_000:
        return 7
    return 10


def _sample_excerpts_positional(
    full_text: str,
    num_samples: int,
    chars_per_sample: int,
) -> list[str]:
    """Evenly-spaced positional sampling as fallback."""
    text_len = len(full_text)
    if text_len <= chars_per_sample * 2:
        return [full_text]
    if num_samples == 1:
        return [full_text[:chars_per_sample]]

    excerpts: list[str] = []
    for i in range(num_samples):
        frac = i / max(num_samples - 1, 1)
        center = int(text_len * frac)
        start = max(0, center - chars_per_sample // 2)
        end = min(text_len, start + chars_per_sample)
        start = max(0, end - chars_per_sample)
        excerpts.append(full_text[start:end])
    return excerpts


def _sample_excerpts_by_chapter(
    full_text: str,
    chapters: list[Chapter],
    num_samples: int,
    chars_per_sample: int,
) -> list[str]:
    """Sample one excerpt per selected chapter for maximum coverage.
    Picks chapters evenly spaced across the book."""
    if not chapters or len(chapters) < 2:
        return _sample_excerpts_positional(full_text, num_samples, chars_per_sample)

    step = max(1, len(chapters) // num_samples)
    selected = chapters[::step][:num_samples]

    if len(selected) < num_samples:
        remaining = [c for c in chapters if c not in selected]
        for c in remaining:
            if len(selected) >= num_samples:
                break
            selected.append(c)
        selected.sort(key=lambda c: c.start_char)

    excerpts: list[str] = []
    for ch in selected:
        start = ch.start_char
        end = min(ch.end_char + 1, start + chars_per_sample, len(full_text))
        if end - start < chars_per_sample and start > 0:
            start = max(0, end - chars_per_sample)
        excerpts.append(full_text[start:end])

    return excerpts


def _sample_excerpts(
    full_text: str,
    num_samples: int | None = None,
    chars_per_sample: int | None = None,
    chapters: list[Chapter] | None = None,
) -> list[str]:
    """Sample excerpts using chapter-aware strategy when possible."""
    n = num_samples or _compute_num_samples(len(full_text))
    cps = chars_per_sample or settings.chars_per_sample

    if chapters and len(chapters) >= 3:
        return _sample_excerpts_by_chapter(full_text, chapters, n, cps)
    return _sample_excerpts_positional(full_text, n, cps)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_from_excerpt(text: str) -> list[dict]:
    """Extract characters from a single excerpt via LLM (pass 1 -- broad)."""
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


def _merge_character_lists(all_lists: list[list[dict]], max_chars: int) -> list[dict]:
    """Pass 2 -- LLM merges, deduplicates, and ranks all discovered characters."""
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


def _parse_characters(merged: list[dict], max_chars: int) -> list[CharacterInfo]:
    """Convert raw LLM output dicts to CharacterInfo objects."""
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


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_characters(
    full_text: str,
    max_chars: int | None = None,
    chapters: list[Chapter] | None = None,
) -> list[CharacterInfo]:
    """Two-pass character extraction with chapter-aware sampling.

    Pass 1: Sample excerpts across the book and extract ALL named characters
            from each excerpt in parallel (broad recall).
    Pass 2: LLM merges, deduplicates, and ranks the union list, trimming to
            the top max_chars characters.
    """
    if not full_text.strip():
        return []

    mc = max_chars or settings.max_characters

    excerpts = _sample_excerpts(full_text, chapters=chapters)
    logger.info("Character extraction: %d excerpts of ~%d chars from %d-char text",
                len(excerpts), settings.chars_per_sample, len(full_text))

    all_lists: list[list[dict]] = []
    if len(excerpts) == 1:
        try:
            all_lists.append(_extract_from_excerpt(excerpts[0]))
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Character extraction from excerpt failed: %s", e)
    else:
        with ThreadPoolExecutor(max_workers=min(len(excerpts), 8)) as pool:
            futures = {
                pool.submit(_extract_from_excerpt, ex): i
                for i, ex in enumerate(excerpts)
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    all_lists.append(result)
                except Exception as e:
                    logger.warning("Character extraction from excerpt failed: %s", e)

    if not all_lists:
        raise ValueError("All character extraction attempts failed")

    total_raw = sum(len(lst) for lst in all_lists)
    logger.info("Pass 1 found %d raw character entries across %d excerpts",
                total_raw, len(all_lists))

    try:
        merged = _merge_character_lists(all_lists, max_chars=mc)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Merge failed, using first list: %s", e)
        merged = all_lists[0]

    result = _parse_characters(merged, mc)
    logger.info("Pass 2 merged to %d final characters", len(result))
    return result


# ---------------------------------------------------------------------------
# Relationship extraction
# ---------------------------------------------------------------------------

def extract_relationships(
    full_text: str,
    characters: list[CharacterInfo],
    chapters: list[Chapter] | None = None,
) -> list[CharacterRelationship]:
    """Extract relationships between characters using LLM."""
    if len(characters) < 2:
        return []

    chars_json = json.dumps(
        [{"name": c.name, "description": c.description or ""} for c in characters],
        indent=2,
    )

    excerpts = _sample_excerpts(
        full_text, num_samples=5, chars_per_sample=4000, chapters=chapters,
    )
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


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

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
