"""Tests for API endpoints (no LLM or external calls)."""
import json
from pathlib import Path

from app.models.schemas import CharacterInfo
from app.services.book_store import save_book


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestBooksEndpoints:
    def test_list_empty(self, client):
        r = client.get("/books")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_after_save(self, client, tmp_data_dir):
        save_book("book_1", "My Story", [CharacterInfo(id="c1", name="Hero")])
        r = client.get("/books")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["title"] == "My Story"

    def test_get_existing(self, client, tmp_data_dir):
        save_book("book_x", "Test Book", [CharacterInfo(id="c1", name="Alice")])
        r = client.get("/books/book_x")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == "book_x"
        assert body["title"] == "Test Book"
        assert "c1" in body["character_ids"]

    def test_get_not_found(self, client):
        r = client.get("/books/doesnt_exist")
        assert r.status_code == 404

    def test_get_book_with_status(self, client, tmp_data_dir):
        save_book("book_s", "Status Book", [], status="processing")
        r = client.get("/books/book_s")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "processing"
        assert body["character_ids"] == []

    def test_upload_non_pdf(self, client):
        r = client.post(
            "/books/upload",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )
        assert r.status_code == 400
        assert "PDF" in r.json()["detail"]

    def test_upload_invalid_pdf_magic_bytes(self, client, tmp_data_dir):
        r = client.post(
            "/books/upload",
            files={"file": ("fake.pdf", b"this is not a real PDF file", "application/pdf")},
        )
        assert r.status_code == 400
        assert "valid PDF" in r.json()["detail"]

    def test_upload_file_too_large(self, client, tmp_data_dir):
        from unittest.mock import patch
        with patch("app.config.settings.max_upload_size_mb", 0):
            r = client.post(
                "/books/upload",
                files={"file": ("big.pdf", b"%PDF-1.4 some content", "application/pdf")},
            )
            assert r.status_code == 413
            assert "too large" in r.json()["detail"]


class TestCharacterEndpoints:
    def test_list_characters(self, client, tmp_data_dir):
        chars = [
            CharacterInfo(id="c1", name="Alice", description="Curious"),
            CharacterInfo(id="c2", name="Cat"),
        ]
        save_book("book_ch", "Test", chars)
        r = client.get("/books/book_ch/characters")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        names = {c["name"] for c in data}
        assert names == {"Alice", "Cat"}

    def test_list_characters_no_book(self, client):
        r = client.get("/books/nonexist/characters")
        assert r.status_code == 404

    def test_get_single_character(self, client, tmp_data_dir):
        chars = [CharacterInfo(id="c1", name="Alice", description="Curious")]
        save_book("book_sc", "Test", chars)
        r = client.get("/books/book_sc/characters/c1")
        assert r.status_code == 200
        assert r.json()["name"] == "Alice"

    def test_get_character_not_found(self, client, tmp_data_dir):
        save_book("book_cn", "Test", [CharacterInfo(id="c1", name="Alice")])
        r = client.get("/books/book_cn/characters/c_nope")
        assert r.status_code == 404


class TestChatEndpoints:
    def test_message_character_not_found(self, client, tmp_data_dir):
        r = client.post(
            "/chat/message",
            json={
                "book_id": "book_nope",
                "character_id": "c1",
                "message": "Hello",
            },
        )
        assert r.status_code == 404

    def test_stream_character_not_found(self, client, tmp_data_dir):
        r = client.post(
            "/chat/stream",
            json={
                "book_id": "book_nope",
                "character_id": "c1",
                "message": "Hello",
            },
        )
        assert r.status_code == 404


class TestConversationHistoryEndpoints:
    def test_get_history_empty(self, client, tmp_data_dir):
        r = client.get("/chat/history/book1/char1")
        assert r.status_code == 200
        data = r.json()
        assert data["messages"] == []
        assert data["memory_summary"] == ""

    def test_clear_history(self, client, tmp_data_dir):
        r = client.delete("/chat/history/book1/char1")
        assert r.status_code == 200
        assert r.json()["status"] == "cleared"


class TestGroupChatEndpoints:
    def test_group_stream_no_characters(self, client, tmp_data_dir):
        r = client.post(
            "/chat/group/stream",
            json={
                "book_id": "b1",
                "character_ids": [],
                "message": "Hello",
            },
        )
        assert r.status_code == 400

    def test_group_message_no_characters(self, client, tmp_data_dir):
        r = client.post(
            "/chat/group/message",
            json={
                "book_id": "b1",
                "character_ids": [],
                "message": "Hello",
            },
        )
        assert r.status_code == 400
