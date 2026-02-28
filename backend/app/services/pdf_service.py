"""PDF ingestion: extract text and chunk for RAG."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from dataclasses import dataclass

import pymupdf
import pdfplumber


@dataclass
class TextChunk:
    text: str
    page: int
    start_char: int
    end_char: int
    chunk_index: int


def extract_text(pdf_path: Path) -> tuple[str, list[tuple[int, str]]]:
    """
    Extract full text and per-page text. Tries PyMuPDF first, falls back to pdfplumber.
    Returns (full_text, [(page_number, page_text), ...]).
    """
    full_parts: list[str] = []
    pages: list[tuple[int, str]] = []

    try:
        doc = pymupdf.open(pdf_path)
        for i, page in enumerate(doc):
            pnum = i + 1
            t = page.get_text()
            text = _clean_text(t)
            full_parts.append(text)
            pages.append((pnum, text))
        doc.close()
        full = "\n\n".join(full_parts)
        return full, pages
    except Exception:
        pass

    try:
        with pdfplumber.open(pdf_path) as doc:
            for i, page in enumerate(doc.pages):
                pnum = i + 1
                t = page.extract_text() or ""
                text = _clean_text(t)
                full_parts.append(text)
                pages.append((pnum, text))
        full = "\n\n".join(full_parts)
        return full, pages
    except Exception as e:
        raise RuntimeError(f"PDF text extraction failed: {e}") from e


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def chunk_text(
    full_text: str,
    pages: list[tuple[int, str]],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks and assign page numbers by mapping
    character ranges back to page content.
    """
    if not full_text.strip():
        return []

    page_offsets: list[int] = [0]
    for _, pt in pages:
        page_offsets.append(page_offsets[-1] + len(pt) + 2)  # +2 for "\n\n"

    chunks: list[TextChunk] = []
    start = 0
    idx = 0
    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        # Prefer breaking at sentence or paragraph
        if end < len(full_text):
            for sep in (". ", "\n\n", "\n", " "):
                last = full_text.rfind(sep, start, end + 1)
                if last != -1:
                    end = last + len(sep)
                    break
        text = full_text[start:end].strip()
        if text:
            page = _char_offset_to_page(start, page_offsets, len(pages))
            chunks.append(
                TextChunk(
                    text=text,
                    page=page,
                    start_char=start,
                    end_char=end,
                    chunk_index=idx,
                )
            )
            idx += 1
        start = end - chunk_overlap if (end - chunk_overlap) > start else end

    return chunks


def _char_offset_to_page(offset: int, page_offsets: list[int], num_pages: int) -> int:
    for p in range(num_pages):
        if p + 1 < len(page_offsets) and offset < page_offsets[p + 1]:
            return p + 1
    return max(1, num_pages)


def generate_book_id() -> str:
    return f"book_{uuid.uuid4().hex[:12]}"
