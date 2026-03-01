"""Tests for the JSON file-based book store."""
import json
from pathlib import Path

from app.models.schemas import BookInfo, CharacterInfo
from app.services.book_store import (
    get_character,
    list_books,
    load_book,
    load_book_with_characters,
    save_book,
    update_book_status,
)


class TestSaveAndLoad:
    def test_save_and_load(self, tmp_data_dir):
        chars = [
            CharacterInfo(id="c1", name="Alice", description="Curious girl."),
            CharacterInfo(id="c2", name="Cat", description="Grinning cat."),
        ]
        save_book("book_abc", "Wonderland", chars)

        book = load_book("book_abc")
        assert book is not None
        assert book.id == "book_abc"
        assert book.title == "Wonderland"
        assert set(book.character_ids) == {"c1", "c2"}

    def test_load_nonexistent(self, tmp_data_dir):
        assert load_book("book_nope") is None

    def test_load_with_characters(self, tmp_data_dir):
        chars = [CharacterInfo(id="c1", name="Alice")]
        save_book("book_x", "Test", chars)

        info, char_list = load_book_with_characters("book_x")
        assert info is not None
        assert len(char_list) == 1
        assert char_list[0].name == "Alice"


class TestListBooks:
    def test_empty(self, tmp_data_dir):
        assert list_books() == []

    def test_multiple(self, tmp_data_dir):
        for i in range(3):
            save_book(f"book_{i}", f"Book {i}", [])
        books = list_books()
        assert len(books) == 3
        titles = [b.title for b in books]
        assert titles == sorted(titles)


class TestGetCharacter:
    def test_found(self, tmp_data_dir):
        chars = [
            CharacterInfo(id="c1", name="Alice"),
            CharacterInfo(id="c2", name="Bob"),
        ]
        save_book("book_gc", "Test", chars)
        c = get_character("book_gc", "c2")
        assert c is not None
        assert c.name == "Bob"

    def test_not_found(self, tmp_data_dir):
        save_book("book_gc2", "Test", [CharacterInfo(id="c1", name="Alice")])
        assert get_character("book_gc2", "c_missing") is None

    def test_wrong_book(self, tmp_data_dir):
        assert get_character("book_doesnt_exist", "c1") is None


class TestUpdateBookStatus:
    def test_update_to_ready_with_characters(self, tmp_data_dir):
        save_book("book_proc", "Processing Book", [], status="processing")
        book = load_book("book_proc")
        assert book.status == "processing"
        assert book.character_ids == []

        chars = [CharacterInfo(id="c1", name="Alice")]
        update_book_status("book_proc", "ready", characters=chars)
        book = load_book("book_proc")
        assert book.status == "ready"
        assert "c1" in book.character_ids

    def test_update_to_error(self, tmp_data_dir):
        save_book("book_err", "Error Book", [], status="processing")
        update_book_status("book_err", "error", error="LLM failed")
        book = load_book("book_err")
        assert book.status == "error"
        assert book.error == "LLM failed"

    def test_update_nonexistent_does_nothing(self, tmp_data_dir):
        update_book_status("nope", "ready")

    def test_save_with_processing_status(self, tmp_data_dir):
        save_book("book_ps", "Test", [], status="processing")
        book = load_book("book_ps")
        assert book.status == "processing"
