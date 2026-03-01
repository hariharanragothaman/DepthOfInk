"""PDF ingestion: extract text and chunk for RAG."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from dataclasses import dataclass

import pymupdf
import pdfplumber


@dataclass
class Chapter:
    number: int
    title: str
    start_char: int
    end_char: int


@dataclass
class TextChunk:
    text: str
    page: int
    start_char: int
    end_char: int
    chunk_index: int
    chapter: int | None = None
    chapter_title: str | None = None


def detect_chapters(full_text: str) -> list[Chapter]:
    """
    Detect chapter boundaries using regex patterns.
    Returns a list of Chapter objects. If no chapters detected, returns empty list.
    """
    chapters: list[Chapter] = []
    patterns = [
        # Chapter \d+ (case insensitive)
        (re.compile(r"(?i)\bchapter\s+(\d+)\b", re.MULTILINE), "chapter"),
        # CHAPTER [IVXLC]+ (Roman numerals)
        (re.compile(r"\bCHAPTER\s+([IVXLC]+)\b", re.MULTILINE), "roman"),
        # Part \d+ (case insensitive)
        (re.compile(r"(?i)\bpart\s+(\d+)\b", re.MULTILINE), "part"),
    ]
    seen_starts: set[int] = set()
    for pattern, kind in patterns:
        for m in pattern.finditer(full_text):
            pos = m.start()
            if pos in seen_starts:
                continue
            seen_starts.add(pos)
            title = m.group(0).strip()
            num_str = m.group(1)
            if kind == "roman":
                num = _roman_to_int(num_str)
            else:
                num = int(num_str)
            chapters.append(
                Chapter(number=num, title=title, start_char=pos, end_char=pos)
            )
    chapters.sort(key=lambda c: c.start_char)
    # Set end_char for each chapter (next chapter start or end of text)
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch.end_char = chapters[i + 1].start_char - 1
        else:
            ch.end_char = len(full_text) - 1
    # For short docs: numbered patterns like "1." at start of line
    if not chapters and len(full_text) < 5000:
        short_pattern = re.compile(r"^\s*(\d+)\.\s+", re.MULTILINE)
        for m in short_pattern.finditer(full_text):
            pos = m.start()
            num = int(m.group(1))
            if num <= 99:  # reasonable chapter number
                chapters.append(
                    Chapter(
                        number=num,
                        title=m.group(0).strip(),
                        start_char=pos,
                        end_char=pos,
                    )
                )
        chapters.sort(key=lambda c: c.start_char)
        for i, ch in enumerate(chapters):
            if i + 1 < len(chapters):
                ch.end_char = chapters[i + 1].start_char - 1
            else:
                ch.end_char = len(full_text) - 1
    return chapters


def _roman_to_int(s: str) -> int:
    rom = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    val = 0
    prev = 0
    for c in reversed(s.upper()):
        n = rom.get(c, 0)
        val += -n if n < prev else n
        prev = n
    return val


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
    chapters: list[Chapter] | None = None,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks and assign page numbers by mapping
    character ranges back to page content. Optionally assign chapter metadata
    when chapters are provided.
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
            chapter_num, chapter_title = _char_offset_to_chapter(
                start, chapters
            )
            chunks.append(
                TextChunk(
                    text=text,
                    page=page,
                    start_char=start,
                    end_char=end,
                    chunk_index=idx,
                    chapter=chapter_num,
                    chapter_title=chapter_title,
                )
            )
            idx += 1
        start = end - chunk_overlap if (end - chunk_overlap) > start else end

    return chunks


def _char_offset_to_chapter(
    offset: int, chapters: list[Chapter] | None
) -> tuple[int | None, str | None]:
    """Return (chapter_number, chapter_title) for the given character offset."""
    if not chapters:
        return None, None
    for ch in reversed(chapters):
        if ch.start_char <= offset <= ch.end_char:
            return ch.number, ch.title
    return None, None


def _char_offset_to_page(offset: int, page_offsets: list[int], num_pages: int) -> int:
    for p in range(num_pages):
        if p + 1 < len(page_offsets) and offset < page_offsets[p + 1]:
            return p + 1
    return max(1, num_pages)


def generate_book_id() -> str:
    return f"book_{uuid.uuid4().hex[:12]}"
