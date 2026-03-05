"""Tests for API endpoints (no LLM or external calls)."""
import asyncio
import json
from pathlib import Path

from app.config import settings
from app.models.schemas import CharacterInfo
from app.services.book_store import save_book


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "checks" in body
        assert body["checks"]["data_dir"] == "ok"
        assert body["checks"]["uploads_dir"] == "ok"
        assert body["checks"]["chroma_dir"] == "ok"
        assert body["checks"]["chromadb"] == "ok"


class TestCORS:
    def test_allowed_origin(self, client):
        r = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin(self, client):
        r = client.options(
            "/health",
            headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "GET"},
        )
        assert r.headers.get("access-control-allow-origin") is None


class TestInputSanitization:
    def test_chat_message_too_long(self, client, tmp_data_dir):
        r = client.post(
            "/chat/message",
            json={
                "book_id": "b1",
                "character_id": "c1",
                "message": "x" * 5001,
            },
        )
        assert r.status_code == 422

    def test_chat_message_empty(self, client, tmp_data_dir):
        r = client.post(
            "/chat/message",
            json={
                "book_id": "b1",
                "character_id": "c1",
                "message": "",
            },
        )
        assert r.status_code == 422


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


class TestConcurrentUploads:
    def test_rejects_when_semaphore_exhausted(self, client, tmp_data_dir):
        from unittest.mock import PropertyMock, patch
        from app.api.routes import books as books_mod
        original = books_mod._upload_semaphore
        exhausted = asyncio.Semaphore(0)
        books_mod._upload_semaphore = exhausted
        try:
            r = client.post(
                "/books/upload",
                files={"file": ("test.pdf", b"%PDF-1.4 content", "application/pdf")},
            )
            assert r.status_code == 429
            assert "Too many uploads" in r.json()["detail"]
        finally:
            books_mod._upload_semaphore = original


class TestDeleteBookEndpoint:
    def test_delete_existing(self, client, tmp_data_dir):
        save_book("book_del", "Deletable", [CharacterInfo(id="c1", name="Hero")])
        r = client.delete("/books/book_del")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"
        r2 = client.get("/books/book_del")
        assert r2.status_code == 404

    def test_delete_not_found(self, client, tmp_data_dir):
        r = client.delete("/books/nonexist")
        assert r.status_code == 404

    def test_delete_removes_from_list(self, client, tmp_data_dir):
        save_book("book_d2", "ToDelete", [])
        assert len(client.get("/books").json()) == 1
        client.delete("/books/book_d2")
        assert len(client.get("/books").json()) == 0


class TestRetryEndpoint:
    def test_retry_error_book_missing_pdf(self, client, tmp_data_dir):
        save_book("book_err", "Error Book", [], status="error")
        from app.services.book_store import update_book_status
        update_book_status("book_err", status="error", error="Something broke")
        r = client.post("/books/book_err/retry")
        assert r.status_code == 410
        assert "no longer available" in r.json()["detail"]

    def test_retry_non_error_book(self, client, tmp_data_dir):
        save_book("book_ok", "OK Book", [CharacterInfo(id="c1", name="A")])
        r = client.post("/books/book_ok/retry")
        assert r.status_code == 409

    def test_retry_not_found(self, client, tmp_data_dir):
        r = client.post("/books/nonexist/retry")
        assert r.status_code == 404


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


class TestExportConversation:
    def test_export_json_empty(self, client, tmp_data_dir):
        save_book("book_ex", "Export Test", [CharacterInfo(id="c1", name="Alice")])
        r = client.get("/chat/export/book_ex/c1?format=json")
        assert r.status_code == 200
        data = json.loads(r.content)
        assert data["book_title"] == "Export Test"
        assert data["character_name"] == "Alice"
        assert data["messages"] == []
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_export_text_empty(self, client, tmp_data_dir):
        save_book("book_ex2", "Text Export", [CharacterInfo(id="c1", name="Bob")])
        r = client.get("/chat/export/book_ex2/c1?format=text")
        assert r.status_code == 200
        assert "text/plain" in r.headers.get("content-type", "")
        text = r.content.decode()
        assert "Text Export" in text
        assert "Bob" in text

    def test_export_json_with_messages(self, client, tmp_data_dir):
        from app.services import conversation_store
        save_book("book_ex3", "Story", [CharacterInfo(id="c1", name="Eve")])
        conversation_store.save_messages("book_ex3", "c1", [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ])
        r = client.get("/chat/export/book_ex3/c1?format=json")
        assert r.status_code == 200
        data = json.loads(r.content)
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "Hello"

    def test_export_text_with_messages(self, client, tmp_data_dir):
        from app.services import conversation_store
        save_book("book_ex4", "Story", [CharacterInfo(id="c1", name="Eve")])
        conversation_store.save_messages("book_ex4", "c1", [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Greetings!"},
        ])
        r = client.get("/chat/export/book_ex4/c1?format=text")
        text = r.content.decode()
        assert "You: Hello" in text
        assert "Eve: Greetings!" in text

    def test_export_book_not_found(self, client, tmp_data_dir):
        r = client.get("/chat/export/nonexist/c1?format=json")
        assert r.status_code == 404

    def test_export_character_not_found(self, client, tmp_data_dir):
        save_book("book_ex5", "Test", [CharacterInfo(id="c1", name="A")])
        r = client.get("/chat/export/book_ex5/c99?format=json")
        assert r.status_code == 404

    def test_export_invalid_format(self, client, tmp_data_dir):
        save_book("book_ex6", "Test", [CharacterInfo(id="c1", name="A")])
        r = client.get("/chat/export/book_ex6/c1?format=csv")
        assert r.status_code == 422


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
