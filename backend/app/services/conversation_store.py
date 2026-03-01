"""JSON-file backed conversation store."""
from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


def _conv_path(book_id: str, character_id: str) -> Path:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir / "conversations" / f"{book_id}_{character_id}.json"


def save_messages(book_id: str, character_id: str, messages: list[dict]) -> None:
    """Append messages to the JSON file. JSON structure: {"messages": [...], "memory_summary": ""}"""
    path = _conv_path(book_id, character_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        existing = data.get("messages", [])
        data["messages"] = existing + messages
    else:
        data = {"messages": messages, "memory_summary": ""}

    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_messages(book_id: str, character_id: str) -> list[dict]:
    """Return all stored messages."""
    path = _conv_path(book_id, character_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("messages", [])


def get_memory_summary(book_id: str, character_id: str) -> str:
    """Return the memory_summary string."""
    path = _conv_path(book_id, character_id)
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("memory_summary", "")


def update_memory_summary(book_id: str, character_id: str, summary: str) -> None:
    """Update just the summary field."""
    path = _conv_path(book_id, character_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"messages": [], "memory_summary": ""}

    data["memory_summary"] = summary
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_conversation(book_id: str, character_id: str) -> None:
    """Delete the conversation file."""
    path = _conv_path(book_id, character_id)
    if path.exists():
        path.unlink()
