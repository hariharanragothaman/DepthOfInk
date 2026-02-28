"""Tests for chat prompt building (no LLM calls)."""
from app.models.schemas import CharacterInfo
from app.services.chat_service import build_system_prompt, format_context


class TestBuildSystemPrompt:
    def test_contains_character_name(self):
        char = CharacterInfo(id="c1", name="Alice", description="A curious girl.")
        prompt = build_system_prompt(char, "")
        assert "Alice" in prompt
        assert "curious girl" in prompt.lower() or "A curious girl" in prompt

    def test_contains_context(self):
        char = CharacterInfo(id="c1", name="Alice")
        prompt = build_system_prompt(char, "[Page 1]\nSome passage text.")
        assert "Some passage text" in prompt
        assert "[Page 1]" in prompt

    def test_includes_example_quotes(self):
        char = CharacterInfo(
            id="c1",
            name="Alice",
            example_quotes=["Curiouser and curiouser!", "Oh dear!"],
        )
        prompt = build_system_prompt(char, "")
        assert "Curiouser and curiouser!" in prompt

    def test_no_break_character_instruction(self):
        char = CharacterInfo(id="c1", name="Alice")
        prompt = build_system_prompt(char, "")
        assert "Do not break character" in prompt

    def test_empty_context_omits_block(self):
        char = CharacterInfo(id="c1", name="Alice")
        prompt = build_system_prompt(char, "")
        assert "Relevant passages" not in prompt


class TestFormatContext:
    def test_single(self):
        ctx = format_context([{"text": "Hello world", "page": 3}])
        assert "[Page 3]" in ctx
        assert "Hello world" in ctx

    def test_multiple(self):
        citations = [
            {"text": "First", "page": 1},
            {"text": "Second", "page": 5},
        ]
        ctx = format_context(citations)
        assert "[Page 1]" in ctx
        assert "[Page 5]" in ctx

    def test_empty(self):
        assert format_context([]) == ""
