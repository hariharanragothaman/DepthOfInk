"""In-memory book metadata store (MVP). Replace with DB later."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from app.config import settings
from app.models.schemas import BookInfo, CharacterInfo, CharacterRelationship

logger = logging.getLogger(__name__)


def _meta_path(book_id: str) -> Path:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir / "books" / f"{book_id}.json"


def save_book(
    book_id: str,
    title: str,
    characters: list[CharacterInfo],
    relationships: list[CharacterRelationship] | None = None,
    status: str = "ready",
) -> None:
    path = _meta_path(book_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id": book_id,
        "title": title,
        "status": status,
        "characters": [c.model_dump() for c in characters],
        "relationships": [r.model_dump() for r in (relationships or [])],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_book_status(
    book_id: str,
    status: str,
    characters: list[CharacterInfo] | None = None,
    relationships: list[CharacterRelationship] | None = None,
    error: str | None = None,
) -> None:
    """Patch status, characters, and relationships on an existing book record."""
    path = _meta_path(book_id)
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = status
    if characters is not None:
        data["characters"] = [c.model_dump() for c in characters]
    if relationships is not None:
        data["relationships"] = [r.model_dump() for r in relationships]
    if error is not None:
        data["error"] = error
    elif "error" in data:
        data.pop("error", None)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_book(book_id: str) -> BookInfo | None:
    path = _meta_path(book_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    chars = [CharacterInfo(**c) for c in data.get("characters", [])]
    return BookInfo(
        id=data["id"],
        title=data.get("title", "Untitled"),
        character_ids=[c.id for c in chars],
        status=data.get("status", "ready"),
        error=data.get("error"),
    )


def load_book_with_characters(book_id: str) -> tuple[BookInfo | None, list[CharacterInfo]]:
    path = _meta_path(book_id)
    if not path.exists():
        return None, []
    data = json.loads(path.read_text(encoding="utf-8"))
    chars = [CharacterInfo(**c) for c in data.get("characters", [])]
    info = BookInfo(
        id=data["id"],
        title=data.get("title", "Untitled"),
        character_ids=[c.id for c in chars],
        status=data.get("status", "ready"),
        error=data.get("error"),
    )
    return info, chars


def load_relationships(book_id: str) -> list[CharacterRelationship]:
    path = _meta_path(book_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [CharacterRelationship(**r) for r in data.get("relationships", [])]


def save_relationships(book_id: str, relationships: list[CharacterRelationship]) -> None:
    """Update just the relationships in an existing book record."""
    path = _meta_path(book_id)
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["relationships"] = [r.model_dump() for r in relationships]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_books() -> list[BookInfo]:
    books_dir = settings.data_dir / "books"
    if not books_dir.exists():
        return []
    out: list[BookInfo] = []
    for p in books_dir.glob("*.json"):
        try:
            b = load_book(p.stem)
            if b:
                out.append(b)
        except Exception:
            continue
    return sorted(out, key=lambda x: x.title)


def get_character(book_id: str, character_id: str) -> CharacterInfo | None:
    _, chars = load_book_with_characters(book_id)
    for c in chars:
        if c.id == character_id:
            return c
    return None


def delete_book(book_id: str) -> bool:
    """Delete a book and all associated data (PDF, embeddings, conversations).

    Returns True if the book existed and was deleted, False if not found.
    """
    meta = _meta_path(book_id)
    if not meta.exists():
        return False

    meta.unlink(missing_ok=True)

    pdf_path = settings.uploads_dir / f"{book_id}.pdf"
    pdf_path.unlink(missing_ok=True)

    chroma_path = settings.chroma_dir / book_id
    if chroma_path.exists():
        shutil.rmtree(chroma_path, ignore_errors=True)

    conv_dir = settings.data_dir / "conversations"
    if conv_dir.exists():
        for p in conv_dir.glob(f"{book_id}_*.json"):
            p.unlink(missing_ok=True)

    logger.info("Deleted book %s and all associated data", book_id)
    return True
