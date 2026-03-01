"""Tests for character extraction helpers and multi-sample logic."""
from app.services.character_service import _slug, _strip_json_block, _sample_excerpts


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


class TestSampleExcerpts:
    def test_short_text_single_sample(self):
        text = "A" * 5000
        excerpts = _sample_excerpts(text, num_samples=3, chars_per_sample=6000)
        assert len(excerpts) == 1
        assert excerpts[0] == text

    def test_long_text_three_samples(self):
        text = "A" * 100_000
        excerpts = _sample_excerpts(text, num_samples=3, chars_per_sample=6000)
        assert len(excerpts) == 3
        for e in excerpts:
            assert len(e) == 6000

    def test_samples_from_different_positions(self):
        text = "A" * 20000 + "B" * 20000 + "C" * 20000
        excerpts = _sample_excerpts(text, num_samples=3, chars_per_sample=5000)
        assert len(excerpts) == 3
        assert "A" in excerpts[0]
        assert "B" in excerpts[1]
        assert "C" in excerpts[2]

    def test_single_sample(self):
        text = "Hello world " * 5000
        excerpts = _sample_excerpts(text, num_samples=1, chars_per_sample=6000)
        assert len(excerpts) == 1
        assert len(excerpts[0]) == 6000

    def test_two_samples(self):
        text = "X" * 50000
        excerpts = _sample_excerpts(text, num_samples=2, chars_per_sample=6000)
        assert len(excerpts) == 2


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
