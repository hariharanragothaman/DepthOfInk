"""Tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    BookCreate,
    BookInfo,
    CharacterInfo,
    ChatChunk,
    ChatMessage,
    ChatRequest,
)


class TestBookInfo:
    def test_minimal(self):
        b = BookInfo(id="b1", title="Test")
        assert b.id == "b1"
        assert b.character_ids == []

    def test_with_characters(self):
        b = BookInfo(id="b2", title="Book", character_ids=["c1", "c2"])
        assert len(b.character_ids) == 2


class TestCharacterInfo:
    def test_defaults(self):
        c = CharacterInfo(id="c1", name="Alice")
        assert c.description is None
        assert c.example_quotes == []

    def test_full(self):
        c = CharacterInfo(
            id="c1",
            name="Alice",
            description="A curious girl.",
            example_quotes=["Curiouser!"],
        )
        assert c.description == "A curious girl."


class TestChatMessage:
    def test_minimal(self):
        m = ChatMessage(role="user", content="Hi")
        assert m.citations == []

    def test_with_citation(self):
        m = ChatMessage(
            role="assistant",
            content="Hello",
            citations=[{"text": "passage", "page": 1}],
        )
        assert len(m.citations) == 1


class TestChatRequest:
    def test_valid(self):
        req = ChatRequest(
            book_id="b1",
            character_id="c1",
            message="Hello",
        )
        assert req.history == []

    def test_with_history(self):
        req = ChatRequest(
            book_id="b1",
            character_id="c1",
            message="Hi",
            history=[ChatMessage(role="user", content="Hey")],
        )
        assert len(req.history) == 1


class TestChatChunk:
    def test_content_chunk(self):
        c = ChatChunk(type="content", content="hello")
        assert c.citation is None

    def test_done_chunk(self):
        c = ChatChunk(type="done")
        assert c.content == ""
