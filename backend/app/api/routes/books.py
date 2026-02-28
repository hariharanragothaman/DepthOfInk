"""Book and PDF upload endpoints."""
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import BookInfo, CharacterInfo
from app.services.book_store import save_book
from app.services.character_service import extract_characters
from app.services.pdf_service import chunk_text, extract_text, generate_book_id
from app.services.rag_service import create_collection

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[BookInfo])
def list_books():
    from app.services.book_store import list_books as _list
    return _list()


@router.get("/{book_id}", response_model=BookInfo)
def get_book(book_id: str):
    from app.services.book_store import load_book
    book = load_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/upload", response_model=BookInfo)
async def upload_pdf(
    file: UploadFile = File(...),
    title: str | None = None,
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    book_id = generate_book_id()
    path = settings.uploads_dir / f"{book_id}.pdf"
    try:
        content = await file.read()
        path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    try:
        full_text, pages = extract_text(path)
    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {str(e)}") from e

    if not full_text.strip():
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="No text could be extracted from the PDF")

    chunks = chunk_text(
        full_text,
        pages,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    create_collection(book_id, chunks)

    try:
        characters = extract_characters(full_text)
    except Exception as e:
        characters = []
        # Log but don't fail: optional
        import logging
        logging.warning("Character extraction failed: %s", e)

    if not characters:
        characters = [
            CharacterInfo(
                id="char_0_narrator",
                name="Narrator",
                description="The voice of the story.",
                example_quotes=[],
            )
        ]

    book_title = title or (file.filename or "Untitled").replace(".pdf", "")
    save_book(book_id, book_title, characters)

    return BookInfo(
        id=book_id,
        title=book_title,
        character_ids=[c.id for c in characters],
    )
