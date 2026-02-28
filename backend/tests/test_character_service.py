"""Tests for character extraction helpers."""
from app.services.character_service import _slug, _strip_json_block


class TestSlug:
    def test_simple(self):
        assert _slug("Alice") == "alice"

    def test_spaces_special(self):
        assert _slug("Cheshire Cat") == "cheshire_cat"

    def test_empty(self):
        assert _slug("") == "unknown"

    def test_unicode(self):
        slug = _slug("Héro 123")
        assert "h" in slug
        assert "123" in slug


class TestStripJsonBlock:
    def test_plain_json(self):
        raw = '{"characters": []}'
        assert _strip_json_block(raw) == raw

    def test_markdown_json_fence(self):
        raw = '```json\n{"characters": []}\n```'
        assert _strip_json_block(raw) == '{"characters": []}'

    def test_plain_fence(self):
        raw = '```\n[]\n```'
        assert _strip_json_block(raw) == '[]'

    def test_no_fence(self):
        raw = '  {"a":1}  '
        assert _strip_json_block(raw) == '{"a":1}'
