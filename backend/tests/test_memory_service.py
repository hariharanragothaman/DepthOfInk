"""Tests for memory service (no LLM calls)."""
from unittest.mock import patch

from app.services.conversation_store import load_messages, save_messages, update_memory_summary
from app.services.memory_service import get_memory_context


class TestGetMemoryContext:
    def test_no_summary(self, tmp_data_dir):
        assert get_memory_context("book1", "char1") is None

    def test_empty_summary(self, tmp_data_dir):
        save_messages("book1", "char1", [{"role": "user", "content": "Hi"}])
        assert get_memory_context("book1", "char1") is None

    def test_has_summary(self, tmp_data_dir):
        update_memory_summary("book1", "char1", "User asked about the plot.")
        ctx = get_memory_context("book1", "char1")
        assert ctx == "User asked about the plot."

    def test_whitespace_summary(self, tmp_data_dir):
        update_memory_summary("book1", "char1", "   ")
        assert get_memory_context("book1", "char1") is None
