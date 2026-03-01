"""Tests for chapter detection in pdf_service."""
from app.services.pdf_service import Chapter, TextChunk, chunk_text, detect_chapters


class TestDetectChapters:
    def test_chapter_digit_pattern(self):
        text = "Intro text.\n\nChapter 1\nFirst chapter content.\n\nChapter 2\nSecond chapter content."
        chapters = detect_chapters(text)
        assert len(chapters) == 2
        assert chapters[0].number == 1
        assert chapters[1].number == 2
        assert chapters[0].start_char < chapters[1].start_char

    def test_chapter_uppercase(self):
        text = "Prologue.\n\nCHAPTER 1\nSome text.\n\nCHAPTER 2\nMore text."
        chapters = detect_chapters(text)
        assert len(chapters) >= 2

    def test_chapter_roman_numerals(self):
        text = "CHAPTER I\nFirst.\n\nCHAPTER II\nSecond.\n\nCHAPTER III\nThird."
        chapters = detect_chapters(text)
        assert len(chapters) == 3
        assert chapters[0].number == 1
        assert chapters[1].number == 2
        assert chapters[2].number == 3

    def test_part_pattern(self):
        text = "Part 1\nIntro.\n\nPart 2\nMiddle.\n\nPart 3\nEnd."
        chapters = detect_chapters(text)
        assert len(chapters) == 3
        assert chapters[0].title.lower().startswith("part")

    def test_no_chapters(self):
        text = "Just some plain text with no chapters or parts."
        chapters = detect_chapters(text)
        assert chapters == []

    def test_end_char_set_correctly(self):
        text = "Chapter 1\nContent one.\n\nChapter 2\nContent two."
        chapters = detect_chapters(text)
        assert len(chapters) == 2
        assert chapters[0].end_char == chapters[1].start_char - 1
        assert chapters[1].end_char == len(text) - 1

    def test_short_doc_numbered_lines(self):
        text = "1. First section.\n2. Second section.\n3. Third section."
        chapters = detect_chapters(text)
        assert len(chapters) == 3

    def test_short_doc_fallback_only_for_short(self):
        text = "1. Section.\n" * 600
        chapters = detect_chapters(text)
        assert chapters == []

    def test_case_insensitive(self):
        text = "chapter 1\nHello.\n\nchapter 2\nWorld."
        chapters = detect_chapters(text)
        assert len(chapters) == 2


class TestChunkTextWithChapters:
    def test_chunks_get_chapter_metadata(self):
        text = "Chapter 1\nFirst chapter content here with enough text.\n\nChapter 2\nSecond chapter content."
        pages = [(1, text)]
        chapters = detect_chapters(text)
        chunks = chunk_text(text, pages, chunk_size=1000, chunk_overlap=10, chapters=chapters)
        assert len(chunks) >= 1
        has_chapter = any(c.chapter is not None for c in chunks)
        assert has_chapter

    def test_chunks_without_chapters(self):
        text = "Some plain text."
        pages = [(1, text)]
        chunks = chunk_text(text, pages, chunk_size=1000, chunk_overlap=10)
        for c in chunks:
            assert c.chapter is None
            assert c.chapter_title is None

    def test_chunk_chapter_assignment(self):
        text = "Chapter 1\n" + "A " * 100 + "\n\nChapter 2\n" + "B " * 100
        pages = [(1, text)]
        chapters = detect_chapters(text)
        chunks = chunk_text(text, pages, chunk_size=50, chunk_overlap=10, chapters=chapters)
        ch1_chunks = [c for c in chunks if c.chapter == 1]
        ch2_chunks = [c for c in chunks if c.chapter == 2]
        assert len(ch1_chunks) > 0
        assert len(ch2_chunks) > 0
