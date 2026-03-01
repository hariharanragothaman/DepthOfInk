"""Tests for group chat service (no LLM calls - just prompt building)."""
from app.models.schemas import CharacterInfo
from app.services.group_chat_service import _build_group_system_prompt
from app.services.chat_service import build_system_prompt


class TestGroupSystemPrompt:
    def test_includes_other_characters(self):
        char = CharacterInfo(id="c1", name="Alice", description="Curious girl.")
        prompt = _build_group_system_prompt(
            char,
            "Some context.",
            other_names=["Cat", "Hatter"],
            prior_replies=["I'm grinning!"],
        )
        assert "Alice" in prompt
        assert "Cat" in prompt
        assert "Hatter" in prompt
        assert "I'm grinning!" in prompt

    def test_no_prior_replies(self):
        char = CharacterInfo(id="c1", name="Alice")
        prompt = _build_group_system_prompt(
            char,
            "",
            other_names=["Cat"],
            prior_replies=[],
        )
        assert "no prior replies yet" in prompt

    def test_no_other_characters(self):
        char = CharacterInfo(id="c1", name="Alice")
        prompt = _build_group_system_prompt(
            char,
            "",
            other_names=[],
            prior_replies=[],
        )
        assert "none" in prompt

    def test_builds_on_base_prompt(self):
        char = CharacterInfo(id="c1", name="Alice", description="A girl.")
        base = build_system_prompt(char, "ctx")
        group = _build_group_system_prompt(char, "ctx", ["Bob"], [])
        assert "Alice" in group
        assert "Do not break character" in group
        assert "Other characters" in group


class TestGroupChatSchemas:
    def test_group_chat_request(self):
        from app.models.schemas import GroupChatRequest
        req = GroupChatRequest(
            book_id="b1",
            character_ids=["c1", "c2"],
            message="Hello everyone!",
        )
        assert len(req.character_ids) == 2
        assert req.history == []

    def test_group_chat_message(self):
        from app.models.schemas import GroupChatMessage
        msg = GroupChatMessage(
            role="assistant",
            content="Hi!",
            character_id="c1",
            character_name="Alice",
        )
        assert msg.character_id == "c1"
        assert msg.character_name == "Alice"
