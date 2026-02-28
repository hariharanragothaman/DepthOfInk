"""Tests for PDF text extraction and chunking."""
from app.services.pdf_service import (
    TextChunk,
    _char_offset_to_page,
    _clean_text,
    chunk_text,
    generate_book_id,
)


class TestCleanText:
    def test_collapses_whitespace(self):
        assert _clean_text("  hello   world  ") == "hello world"

    def test_strips_newlines(self):
        assert _clean_text("line1\n  line2\n\nline3") == "line1 line2 line3"

    def test_empty_string(self):
        assert _clean_text("") == ""

    def test_single_word(self):
        assert _clean_text("  word  ") == "word"


class TestGenerateBookId:
    def test_format(self):
        bid = generate_book_id()
        assert bid.startswith("book_")
        assert len(bid) == len("book_") + 12

    def test_unique(self):
        ids = {generate_book_id() for _ in range(50)}
        assert len(ids) == 50


class TestChunkText:
    def test_empty_text_returns_empty(self):
        assert chunk_text("", []) == []
        assert chunk_text("   ", [(1, "   ")]) == []

    def test_short_text_single_chunk(self):
        text = "Hello world, this is a test."
        pages = [(1, text)]
        chunks = chunk_text(text, pages, chunk_size=1000, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].page == 1
        assert chunks[0].chunk_index == 0

    def test_multiple_chunks_overlap(self):
        text = "A" * 500 + ". " + "B" * 500
        pages = [(1, text)]
        chunks = chunk_text(text, pages, chunk_size=300, chunk_overlap=50)
        assert len(chunks) > 1
        for c in chunks:
            assert isinstance(c, TextChunk)
            assert c.page >= 1
            assert len(c.text) > 0

    def test_multi_page_assignment(self):
        page1 = "First page content here."
        page2 = "Second page content here."
        full = f"{page1}\n\n{page2}"
        pages = [(1, page1), (2, page2)]
        chunks = chunk_text(full, pages, chunk_size=1000, chunk_overlap=10)
        assert len(chunks) >= 1
        assert chunks[0].page == 1

    def test_chunk_indices_sequential(self):
        text = " ".join(f"sentence_{i}" for i in range(100))
        pages = [(1, text)]
        chunks = chunk_text(text, pages, chunk_size=100, chunk_overlap=20)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


class TestCharOffsetToPage:
    def test_first_page(self):
        offsets = [0, 100, 200]
        assert _char_offset_to_page(50, offsets, 2) == 1

    def test_second_page(self):
        offsets = [0, 100, 200]
        assert _char_offset_to_page(150, offsets, 2) == 2

    def test_offset_at_boundary(self):
        offsets = [0, 100, 200]
        assert _char_offset_to_page(100, offsets, 2) == 2

    def test_past_end(self):
        offsets = [0, 100, 200]
        assert _char_offset_to_page(300, offsets, 2) == 2
