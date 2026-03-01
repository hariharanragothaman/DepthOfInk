"""Shared fixtures for backend tests."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ["RATE_LIMIT_ENABLED"] = "false"


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Redirect all data dirs to a temp folder so tests don't touch real data."""
    with (
        patch("app.config.settings.data_dir", tmp_path / "data"),
        patch("app.config.settings.uploads_dir", tmp_path / "uploads"),
        patch("app.config.settings.chroma_dir", tmp_path / "chroma"),
    ):
        (tmp_path / "data" / "books").mkdir(parents=True)
        (tmp_path / "uploads").mkdir(parents=True)
        (tmp_path / "chroma").mkdir(parents=True)
        yield tmp_path


@pytest.fixture()
def client(tmp_data_dir):
    """FastAPI TestClient with temp data dirs."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_book_json():
    """A minimal book metadata dict for testing the store."""
    return {
        "id": "book_test123",
        "title": "Alice in Wonderland",
        "characters": [
            {
                "id": "char_0_alice",
                "name": "Alice",
                "description": "A curious girl who falls down a rabbit hole.",
                "example_quotes": ["Curiouser and curiouser!"],
            },
            {
                "id": "char_1_cheshire_cat",
                "name": "Cheshire Cat",
                "description": "A mischievous, grinning cat.",
                "example_quotes": ["We're all mad here."],
            },
        ],
    }
