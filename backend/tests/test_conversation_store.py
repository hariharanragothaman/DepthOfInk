"""Tests for conversation store."""
from app.services.conversation_store import (
    clear_conversation,
    get_memory_summary,
    load_messages,
    save_messages,
    update_memory_summary,
)


class TestConversationStore:
    def test_save_and_load(self, tmp_data_dir):
        msgs = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        save_messages("book1", "char1", msgs)
        loaded = load_messages("book1", "char1")
        assert len(loaded) == 2
        assert loaded[0]["role"] == "user"
        assert loaded[1]["content"] == "Hi there!"

    def test_append_messages(self, tmp_data_dir):
        save_messages("book1", "char1", [{"role": "user", "content": "Hello"}])
        save_messages("book1", "char1", [{"role": "assistant", "content": "Hi"}])
        loaded = load_messages("book1", "char1")
        assert len(loaded) == 2

    def test_load_empty(self, tmp_data_dir):
        assert load_messages("book_none", "char_none") == []

    def test_memory_summary_default(self, tmp_data_dir):
        assert get_memory_summary("book1", "char1") == ""

    def test_update_memory_summary(self, tmp_data_dir):
        save_messages("book1", "char1", [{"role": "user", "content": "Hi"}])
        update_memory_summary("book1", "char1", "User said hi.")
        assert get_memory_summary("book1", "char1") == "User said hi."

    def test_update_summary_without_prior_messages(self, tmp_data_dir):
        update_memory_summary("book2", "char2", "Summary text")
        assert get_memory_summary("book2", "char2") == "Summary text"
        assert load_messages("book2", "char2") == []

    def test_clear_conversation(self, tmp_data_dir):
        save_messages("book1", "char1", [{"role": "user", "content": "Hi"}])
        update_memory_summary("book1", "char1", "Some summary")
        clear_conversation("book1", "char1")
        assert load_messages("book1", "char1") == []
        assert get_memory_summary("book1", "char1") == ""

    def test_clear_nonexistent(self, tmp_data_dir):
        clear_conversation("book_nope", "char_nope")

    def test_different_characters_isolated(self, tmp_data_dir):
        save_messages("book1", "char_a", [{"role": "user", "content": "Hello A"}])
        save_messages("book1", "char_b", [{"role": "user", "content": "Hello B"}])
        a_msgs = load_messages("book1", "char_a")
        b_msgs = load_messages("book1", "char_b")
        assert len(a_msgs) == 1
        assert a_msgs[0]["content"] == "Hello A"
        assert len(b_msgs) == 1
        assert b_msgs[0]["content"] == "Hello B"
