"""Character detection: prompt-based extraction from book text."""
from __future__ import annotations

import json
import re
from openai import OpenAI

from app.config import settings
from app.models.schemas import CharacterInfo


SYSTEM_EXTRACT = """You are an expert at analyzing narrative text. Given excerpts from a story or book, list the main characters that a reader would want to "talk to" in a chat. Focus on named characters with dialogue or clear presence, not minor walk-ons. Return valid JSON only, no markdown or explanation."""

USER_EXTRACT = """From this book excerpt, list the main characters (typically 2-6). For each character provide:
- name: full or primary name
- description: 1-2 sentences about who they are in the story
- example_quotes: 1-3 short quotes that sound like them (optional but helpful)

Excerpt (first ~8000 chars):
---
{text}
---

Return a JSON object with key "characters" and value an array of objects with keys: name, description, example_quotes (array of strings)."""


def extract_characters(full_text: str, max_chars: int = 12_000) -> list[CharacterInfo]:
    """Use LLM to extract character list and minimal profile from book text."""
    text = full_text[:max_chars].strip()
    if not text:
        return []

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_EXTRACT},
            {"role": "user", "content": USER_EXTRACT.format(text=text)},
        ],
        temperature=0.2,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = _strip_json_block(raw)

    try:
        data = json.loads(raw)
        chars = data.get("characters") or data
        if not isinstance(chars, list):
            chars = [chars]
        out: list[CharacterInfo] = []
        for i, c in enumerate(chars[:10]):
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
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Character extraction JSON parse failed: {e}") from e


def _strip_json_block(s: str) -> str:
    s = s.strip()
    for start in ("```json", "```"):
        if s.startswith(start):
            s = s[len(start) :].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return s


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unknown"
