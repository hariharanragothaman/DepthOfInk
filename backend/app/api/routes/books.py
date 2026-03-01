"""Book and PDF upload endpoints."""
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile

from app.config import settings
from app.models.schemas import BookInfo, CharacterInfo, CharacterRelationship
from app.services.book_store import (
    delete_book as _delete_book,
    load_relationships,
    save_book,
    update_book_status,
)
from app.services.character_service import extract_characters, extract_relationships
from app.services.pdf_service import chunk_text, detect_chapters, extract_text, generate_book_id
from app.services.rag_service import create_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])

def _get_limiter():
    from app.rate_limit import limiter
    return limiter


@router.get("", response_model=list[BookInfo])
@_get_limiter().limit(settings.rate_limit_default)
def list_books(request: Request):
    from app.services.book_store import list_books as _list
    return _list()


@router.get("/{book_id}", response_model=BookInfo)
@_get_limiter().limit(settings.rate_limit_default)
def get_book(request: Request, book_id: str):
    from app.services.book_store import load_book
    book = load_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


def _process_book(book_id: str, full_text: str, pages: list[tuple[int, int]], chapters) -> None:
    """Background processing: embeddings + character/relationship extraction in parallel."""
    try:
        chunks = chunk_text(
            full_text,
            pages,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            chapters=chapters if chapters else None,
        )

        with ThreadPoolExecutor(max_workers=2) as pool:
            embed_future = pool.submit(create_collection, book_id, chunks)
            char_future = pool.submit(
                extract_characters, full_text,
                None, chapters if chapters else None,
            )

            embed_future.result()

            try:
                characters = char_future.result()
            except Exception as e:
                characters = []
                logger.warning("Character extraction failed: %s", e)

        if not characters:
            characters = [
                CharacterInfo(
                    id="char_0_narrator",
                    name="Narrator",
                    description="The voice of the story.",
                    example_quotes=[],
                )
            ]

        relationships: list[CharacterRelationship] = []
        if len(characters) >= 2:
            try:
                relationships = extract_relationships(
                    full_text, characters, chapters if chapters else None,
                )
            except Exception as e:
                logger.warning("Relationship extraction failed: %s", e)

        update_book_status(
            book_id,
            status="ready",
            characters=characters,
            relationships=relationships,
        )
        logger.info("Book %s processing complete: %d characters, %d relationships",
                     book_id, len(characters), len(relationships))
    except Exception as e:
        logger.exception("Background processing failed for book %s", book_id)
        update_book_status(book_id, status="error", error=str(e))


@router.post("/upload", response_model=BookInfo)
@_get_limiter().limit(settings.rate_limit_upload)
async def upload_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = None,
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    book_id = generate_book_id()
    path = settings.uploads_dir / f"{book_id}.pdf"
    try:
        content = await file.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
            )
        if not content[:5].startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="File does not appear to be a valid PDF.",
            )
        path.write_bytes(content)
    except HTTPException:
        raise
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

    chapters = detect_chapters(full_text)
    book_title = title or (file.filename or "Untitled").replace(".pdf", "")

    save_book(book_id, book_title, characters=[], status="processing")

    background_tasks.add_task(_process_book, book_id, full_text, pages, chapters)

    return BookInfo(
        id=book_id,
        title=book_title,
        character_ids=[],
        status="processing",
    )


@router.delete("/{book_id}", status_code=200)
@_get_limiter().limit(settings.rate_limit_default)
def delete_book(request: Request, book_id: str):
    if not _delete_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
    return {"status": "deleted", "book_id": book_id}


@router.post("/{book_id}/retry", response_model=BookInfo)
@_get_limiter().limit(settings.rate_limit_upload)
def retry_processing(request: Request, background_tasks: BackgroundTasks, book_id: str):
    """Re-trigger processing for a book stuck in 'error' state."""
    from app.services.book_store import load_book
    book = load_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.status != "error":
        raise HTTPException(status_code=409, detail="Book is not in error state")

    pdf_path = settings.uploads_dir / f"{book_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=410, detail="PDF file no longer available")

    try:
        full_text, pages = extract_text(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e}") from e

    chapters = detect_chapters(full_text)
    update_book_status(book_id, status="processing")
    background_tasks.add_task(_process_book, book_id, full_text, pages, chapters)

    return BookInfo(
        id=book.id,
        title=book.title,
        character_ids=[],
        status="processing",
    )


@router.get("/{book_id}/relationships", response_model=list[CharacterRelationship])
@_get_limiter().limit(settings.rate_limit_default)
def get_relationships(request: Request, book_id: str):
    """Get character relationship graph for a book."""
    from app.services.book_store import load_book
    book = load_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return load_relationships(book_id)
