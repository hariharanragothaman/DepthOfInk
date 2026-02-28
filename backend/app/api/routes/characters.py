"""Character endpoints."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import CharacterInfo
from app.services.book_store import get_character, load_book_with_characters

router = APIRouter(prefix="/books", tags=["characters"])


@router.get("/{book_id}/characters", response_model=list[CharacterInfo])
def list_characters(book_id: str):
    _, characters = load_book_with_characters(book_id)
    if not characters:
        raise HTTPException(status_code=404, detail="Book not found or has no characters")
    return characters


@router.get("/{book_id}/characters/{character_id}", response_model=CharacterInfo)
def get_character_by_id(book_id: str, character_id: str):
    char = get_character(book_id, character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char
