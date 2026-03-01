"""Tests for character extraction helpers and multi-sample logic."""
from app.services.character_service import (
    _slug,
    _strip_json_block,
    _sample_excerpts,
    _sample_excerpts_positional,
    _sample_excerpts_by_chapter,
    _compute_num_samples,
    _parse_characters,
)
from app.services.pdf_service import Chapter


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


class TestComputeNumSamples:
    def test_tiny_text(self):
        assert _compute_num_samples(5_000) == 1

    def test_short_text(self):
        assert _compute_num_samples(30_000) == 3

    def test_medium_text(self):
        assert _compute_num_samples(80_000) == 5

    def test_long_text(self):
        assert _compute_num_samples(200_000) == 7

    def test_very_long_text(self):
        assert _compute_num_samples(1_000_000) == 10


class TestSampleExcerptsPositional:
    def test_short_text_returns_full(self):
        text = "A" * 5000
        excerpts = _sample_excerpts_positional(text, num_samples=3, chars_per_sample=6000)
        assert len(excerpts) == 1
        assert excerpts[0] == text

    def test_long_text_three_samples(self):
        text = "A" * 100_000
        excerpts = _sample_excerpts_positional(text, num_samples=3, chars_per_sample=6000)
        assert len(excerpts) == 3
        for e in excerpts:
            assert len(e) == 6000

    def test_samples_from_different_positions(self):
        text = "A" * 20000 + "B" * 20000 + "C" * 20000
        excerpts = _sample_excerpts_positional(text, num_samples=3, chars_per_sample=5000)
        assert len(excerpts) == 3
        assert "A" in excerpts[0]
        assert "B" in excerpts[1]
        assert "C" in excerpts[2]

    def test_single_sample(self):
        text = "Hello world " * 5000
        excerpts = _sample_excerpts_positional(text, num_samples=1, chars_per_sample=6000)
        assert len(excerpts) == 1
        assert len(excerpts[0]) == 6000

    def test_five_samples(self):
        text = "X" * 200_000
        excerpts = _sample_excerpts_positional(text, num_samples=5, chars_per_sample=6000)
        assert len(excerpts) == 5

    def test_seven_samples(self):
        text = "X" * 500_000
        excerpts = _sample_excerpts_positional(text, num_samples=7, chars_per_sample=12000)
        assert len(excerpts) == 7
        for e in excerpts:
            assert len(e) == 12000


class TestSampleExcerptsByChapter:
    def _make_chapters(self, n: int, text_len: int) -> list[Chapter]:
        chunk = text_len // n
        return [
            Chapter(number=i + 1, title=f"Chapter {i+1}",
                    start_char=i * chunk, end_char=(i + 1) * chunk - 1)
            for i in range(n)
        ]

    def test_basic_chapter_sampling(self):
        text = "X" * 100_000
        chapters = self._make_chapters(10, 100_000)
        excerpts = _sample_excerpts_by_chapter(text, chapters, num_samples=5, chars_per_sample=6000)
        assert len(excerpts) == 5
        for e in excerpts:
            assert len(e) <= 6000

    def test_falls_back_when_few_chapters(self):
        text = "X" * 100_000
        chapters = [Chapter(number=1, title="Ch 1", start_char=0, end_char=99_999)]
        excerpts = _sample_excerpts_by_chapter(text, chapters, num_samples=3, chars_per_sample=6000)
        assert len(excerpts) == 3

    def test_falls_back_when_no_chapters(self):
        text = "X" * 100_000
        excerpts = _sample_excerpts_by_chapter(text, [], num_samples=3, chars_per_sample=6000)
        assert len(excerpts) == 3

    def test_covers_different_chapters(self):
        text = "A" * 50000 + "B" * 50000 + "C" * 50000 + "D" * 50000 + "E" * 50000
        total = len(text)
        chapters = self._make_chapters(5, total)
        excerpts = _sample_excerpts_by_chapter(text, chapters, num_samples=5, chars_per_sample=10000)
        assert len(excerpts) == 5
        assert "A" in excerpts[0]
        assert "E" in excerpts[-1]


class TestSampleExcerptsIntegrated:
    def test_uses_chapters_when_available(self):
        text = "X" * 100_000
        chunk = 100_000 // 10
        chapters = [
            Chapter(number=i + 1, title=f"Ch {i+1}",
                    start_char=i * chunk, end_char=(i + 1) * chunk - 1)
            for i in range(10)
        ]
        excerpts = _sample_excerpts(text, num_samples=5, chars_per_sample=6000, chapters=chapters)
        assert len(excerpts) == 5

    def test_positional_fallback_without_chapters(self):
        text = "X" * 100_000
        excerpts = _sample_excerpts(text, num_samples=5, chars_per_sample=6000, chapters=None)
        assert len(excerpts) == 5

    def test_auto_num_samples(self):
        text = "X" * 200_000
        excerpts = _sample_excerpts(text, chars_per_sample=6000)
        assert len(excerpts) == 7  # 200K -> 7 samples


class TestParseCharacters:
    def test_basic(self):
        raw = [
            {"name": "Alice", "description": "Curious girl", "example_quotes": ["Down the hole!"]},
            {"name": "Bob", "description": "A friend"},
        ]
        result = _parse_characters(raw, max_chars=12)
        assert len(result) == 2
        assert result[0].name == "Alice"
        assert result[0].example_quotes == ["Down the hole!"]
        assert result[1].name == "Bob"

    def test_max_chars_limit(self):
        raw = [{"name": f"Char{i}"} for i in range(20)]
        result = _parse_characters(raw, max_chars=5)
        assert len(result) == 5

    def test_empty_name_falls_back_to_unknown(self):
        raw = [{"name": ""}, {"name": "Alice"}]
        result = _parse_characters(raw, max_chars=12)
        assert len(result) == 2
        assert result[0].name == "Unknown"
        assert result[1].name == "Alice"

    def test_quotes_as_string(self):
        raw = [{"name": "Test", "example_quotes": "A single quote"}]
        result = _parse_characters(raw, max_chars=12)
        assert result[0].example_quotes == ["A single quote"]

    def test_twenty_char_limit(self):
        raw = [{"name": f"Char{i}"} for i in range(30)]
        result = _parse_characters(raw, max_chars=20)
        assert len(result) == 20


class TestCharacterRelationshipSchema:
    def test_relationship_schema(self):
        from app.models.schemas import CharacterRelationship
        rel = CharacterRelationship(
            source_id="char_0_harry",
            target_id="char_1_ron",
            source_name="Harry Potter",
            target_name="Ron Weasley",
            relationship="best friends",
            description="Loyal friends since first year at Hogwarts.",
        )
        assert rel.source_name == "Harry Potter"
        assert rel.relationship == "best friends"

    def test_relationship_no_description(self):
        from app.models.schemas import CharacterRelationship
        rel = CharacterRelationship(
            source_id="c1",
            target_id="c2",
            source_name="Alice",
            target_name="Bob",
            relationship="siblings",
        )
        assert rel.description is None


class TestBookStoreRelationships:
    def test_save_and_load_relationships(self, tmp_data_dir):
        from app.models.schemas import CharacterInfo, CharacterRelationship
        from app.services.book_store import save_book, load_relationships

        chars = [
            CharacterInfo(id="c1", name="Alice"),
            CharacterInfo(id="c2", name="Bob"),
        ]
        rels = [
            CharacterRelationship(
                source_id="c1", target_id="c2",
                source_name="Alice", target_name="Bob",
                relationship="friends",
            )
        ]
        save_book("book_rel", "Test", chars, rels)
        loaded = load_relationships("book_rel")
        assert len(loaded) == 1
        assert loaded[0].source_name == "Alice"
        assert loaded[0].relationship == "friends"

    def test_load_relationships_empty(self, tmp_data_dir):
        from app.models.schemas import CharacterInfo
        from app.services.book_store import save_book, load_relationships

        save_book("book_norel", "Test", [CharacterInfo(id="c1", name="A")])
        loaded = load_relationships("book_norel")
        assert loaded == []

    def test_load_relationships_no_book(self, tmp_data_dir):
        from app.services.book_store import load_relationships
        assert load_relationships("book_nope") == []

    def test_save_relationships_separately(self, tmp_data_dir):
        from app.models.schemas import CharacterInfo, CharacterRelationship
        from app.services.book_store import save_book, save_relationships, load_relationships

        save_book("book_sr", "Test", [
            CharacterInfo(id="c1", name="A"),
            CharacterInfo(id="c2", name="B"),
        ])
        rels = [
            CharacterRelationship(
                source_id="c1", target_id="c2",
                source_name="A", target_name="B",
                relationship="rivals",
            )
        ]
        save_relationships("book_sr", rels)
        loaded = load_relationships("book_sr")
        assert len(loaded) == 1
        assert loaded[0].relationship == "rivals"


class TestRelationshipsAPI:
    def test_get_relationships(self, client, tmp_data_dir):
        from app.models.schemas import CharacterInfo, CharacterRelationship
        from app.services.book_store import save_book

        chars = [
            CharacterInfo(id="c1", name="Alice"),
            CharacterInfo(id="c2", name="Bob"),
        ]
        rels = [
            CharacterRelationship(
                source_id="c1", target_id="c2",
                source_name="Alice", target_name="Bob",
                relationship="friends",
                description="Close allies.",
            )
        ]
        save_book("book_api_rel", "Test", chars, rels)
        r = client.get("/books/book_api_rel/relationships")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["source_name"] == "Alice"
        assert data[0]["relationship"] == "friends"

    def test_get_relationships_no_book(self, client):
        r = client.get("/books/nope/relationships")
        assert r.status_code == 404

    def test_get_relationships_empty(self, client, tmp_data_dir):
        from app.models.schemas import CharacterInfo
        from app.services.book_store import save_book

        save_book("book_no_rels", "Test", [CharacterInfo(id="c1", name="X")])
        r = client.get("/books/book_no_rels/relationships")
        assert r.status_code == 200
        assert r.json() == []
