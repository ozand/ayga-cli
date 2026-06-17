"""Tests for sources cache utility."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ayga_cli.utils.sources_cache import load_cache, save_cache, clear_cache, CACHE_TTL

SAMPLE_SOURCES = [
    {"name": "web-search", "description": "Web search", "category": "search"},
    {"name": "ai-answer", "description": "AI answers", "category": "ai"},
]


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Redirect cache to a temp directory."""
    cache_file = tmp_path / "sources_cache.json"
    monkeypatch.setattr("ayga_cli.utils.sources_cache.CACHE_PATH", cache_file)
    return cache_file


def test_save_and_load(tmp_cache):
    save_cache(SAMPLE_SOURCES)
    loaded = load_cache()
    assert loaded == SAMPLE_SOURCES


def test_expired_cache(tmp_cache):
    # Write cache with old timestamp
    tmp_cache.parent.mkdir(parents=True, exist_ok=True)
    tmp_cache.write_text(json.dumps({"ts": time.time() - CACHE_TTL - 10, "sources": SAMPLE_SOURCES}))
    result = load_cache()
    assert result is None


def test_fresh_cache(tmp_cache):
    tmp_cache.parent.mkdir(parents=True, exist_ok=True)
    tmp_cache.write_text(json.dumps({"ts": time.time(), "sources": SAMPLE_SOURCES}))
    result = load_cache()
    assert result == SAMPLE_SOURCES


def test_clear_cache(tmp_cache):
    save_cache(SAMPLE_SOURCES)
    assert tmp_cache.exists()
    clear_cache()
    assert not tmp_cache.exists()


def test_load_missing_cache(tmp_cache):
    result = load_cache()
    assert result is None


def test_load_corrupt_cache(tmp_cache):
    tmp_cache.parent.mkdir(parents=True, exist_ok=True)
    tmp_cache.write_text("not valid json {{")
    result = load_cache()
    assert result is None
