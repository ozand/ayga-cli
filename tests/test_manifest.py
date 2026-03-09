"""Tests for manifest cache and fuzzy search."""

import gzip
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aparser_cli.manifest import (
    Manifest,
    ManifestCache,
    ParserInfo,
    ParameterSchema,
    search_parsers,
    get_manifest_cache,
    clear_cache,
)


class TestParameterSchema:
    """Test ParameterSchema model."""

    def test_basic_creation(self):
        """Test basic parameter creation."""
        param = ParameterSchema(
            type="integer",
            description="Number of results",
            required=True,
            default=10,
            min=1,
            max=100,
        )
        assert param.type == "integer"
        assert param.default == 10
        assert param.required is True

    def test_enum_parameter(self):
        """Test enum parameter."""
        param = ParameterSchema(
            type="string",
            enum=["option1", "option2", "option3"],
        )
        assert param.enum == ["option1", "option2", "option3"]


class TestParserInfo:
    """Test ParserInfo model."""

    def test_basic_creation(self):
        """Test basic parser info creation."""
        parser = ParserInfo(
            name="SE::Google",
            description="Google search parser",
        )
        assert parser.name == "SE::Google"
        assert parser.category == "SE"

    def test_explicit_category(self):
        """Test with explicit category."""
        parser = ParserInfo(
            name="SE::Google",
            category="SearchEngines",
        )
        assert parser.category == "SearchEngines"

    def test_no_category_in_name(self):
        """Test parser without :: in name."""
        parser = ParserInfo(name="SimpleParser")
        assert parser.category == "Other"


class TestManifest:
    """Test Manifest model."""

    def test_empty_manifest(self):
        """Test empty manifest creation."""
        manifest = Manifest()
        assert manifest.parsers == {}
        assert manifest.version == "2.1.0"
        assert manifest.created_at is not None

    def test_manifest_with_parsers(self):
        """Test manifest with parsers."""
        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        assert len(manifest.parsers) == 1
        assert "SE::Google" in manifest.parsers

    def test_to_dict(self):
        """Test manifest serialization."""
        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        data = manifest.model_dump()
        assert data["version"] == "2.1.0"
        assert "created_at" in data
        assert "SE::Google" in data["parsers"]

    def test_from_dict(self):
        """Test manifest deserialization."""
        from datetime import timezone
        data = {
            "version": "2.1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "parser_count": 1,
            "parsers": {
                "SE::Google": {
                    "name": "SE::Google",
                    "description": "Google parser",
                    "category": "SE",
                    "parameters": {},
                    "presets": [],
                    "keywords": [],
                }
            },
        }

        manifest = Manifest.model_validate(data)
        assert manifest.version == "2.1.0"
        assert "SE::Google" in manifest.parsers


class TestManifestCache:
    """Test ManifestCache functionality."""

    def test_cache_path(self):
        """Test cache path generation."""
        cache = ManifestCache()
        path = cache._get_cache_path()
        assert "manifest.json.gz" in str(path)

    def test_save_and_load(self, tmp_path):
        """Test saving and loading manifest."""
        cache = ManifestCache()
        cache._cache_path = tmp_path / "test_manifest.json.gz"

        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        cache.save(manifest)
        loaded = cache.load()

        assert loaded is not None
        assert "SE::Google" in loaded.parsers

    def test_is_expired(self, tmp_path):
        """Test expiration check."""
        cache = ManifestCache()
        # Override cache path to use tmp_path
        cache.cache_path = tmp_path / "test_manifest.json.gz"

        # No file exists, so expired
        assert cache.is_expired()

        # Create a fresh cache
        parser = ParserInfo(name="Test", description="Test parser", category="Test")
        manifest = Manifest(parsers={"Test": parser})
        cache.save(manifest)

        # Fresh cache should not be expired
        assert not cache.is_expired()

    def test_get_age_hours(self, tmp_path):
        """Test age calculation."""
        cache = ManifestCache()
        cache.cache_path = tmp_path / "test_manifest.json.gz"

        # No cache
        assert cache.get_age_hours() == float("inf")

        # Fresh cache
        parser = ParserInfo(name="Test", description="Test parser", category="Test")
        manifest = Manifest(parsers={"Test": parser})
        cache.save(manifest)
        age = cache.get_age_hours()
        assert 0 <= age < 1

    def test_clear(self, tmp_path):
        """Test clearing cache."""
        cache = ManifestCache()
        cache.cache_path = tmp_path / "test_manifest.json.gz"

        parser = ParserInfo(name="Test", description="Test parser", category="Test")
        manifest = Manifest(parsers={"Test": parser})
        cache.save(manifest)
        assert cache.cache_path.exists()

        cache.clear()
        assert not cache.cache_path.exists()
        assert cache._manifest is None

    def test_get_parser(self, tmp_path):
        """Test getting parser by name."""
        cache = ManifestCache()
        cache.cache_path = tmp_path / "test_manifest.json.gz"

        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})
        cache.save(manifest)

        # Load manifest and get parser
        loaded_manifest = cache.load()
        assert loaded_manifest is not None
        result = loaded_manifest.get_parser("SE::Google")
        assert result is not None
        assert result.name == "SE::Google"

        # Test getting parser that doesn't exist
        not_found = loaded_manifest.get_parser("NonExistent")
        assert not_found is None


class TestSearch:
    """Test search functionality."""

    def test_exact_match(self):
        """Test exact name match."""
        from aparser_cli.manifest import FuzzySearchIndex

        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        results = index.search("SE::Google")
        assert len(results) == 1
        assert results[0].parser.name == "SE::Google"
        assert results[0].score == 1.0

    def test_partial_match(self):
        """Test partial name match."""
        from aparser_cli.manifest import FuzzySearchIndex

        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        results = index.search("Google")
        assert len(results) == 1
        assert results[0].score >= 0.8

    def test_description_match(self):
        """Test description matching."""
        from aparser_cli.manifest import FuzzySearchIndex

        parser = ParserInfo(name="SE::Google", description="Search engine parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        # Search for "engine" which is in the description
        results = index.search("engine")
        assert len(results) == 1

    def test_category_filter(self):
        """Test category filtering."""
        from aparser_cli.manifest import FuzzySearchIndex

        google = ParserInfo(name="SE::Google", description="Google search", category="SE")
        yandex = ParserInfo(name="SE::Yandex", description="Yandex search", category="SE")
        whois = ParserInfo(name="Net::Whois", description="Whois lookup", category="Net")

        manifest = Manifest(parsers={
            "SE::Google": google,
            "SE::Yandex": yandex,
            "Net::Whois": whois,
        })

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        # Search for "search" which is in SE category descriptions
        results = index.search("search", category="SE")
        assert len(results) == 2
        assert all(r.parser.category == "SE" for r in results)

    def test_limit(self):
        """Test result limiting."""
        from aparser_cli.manifest import FuzzySearchIndex

        parsers = {
            f"Parser{i}": ParserInfo(name=f"Parser{i}", description=f"Desc{i}", category="Test")
            for i in range(20)
        }
        manifest = Manifest(parsers=parsers)

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        results = index.search("parser", limit=5)
        assert len(results) == 5

    def test_min_confidence(self):
        """Test minimum confidence threshold."""
        from aparser_cli.manifest import FuzzySearchIndex

        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        # High threshold should return no results for weak match
        results = index.search("xyz", min_score=0.9)
        assert len(results) == 0

    def test_suggest_parsers(self):
        """Test parser suggestions."""
        from aparser_cli.manifest import FuzzySearchIndex

        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        index = FuzzySearchIndex(manifest)
        index.build(manifest)

        suggestions = index.search("Googl")
        assert len(suggestions) > 0


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_manifest_cache(self):
        """Test global cache getter."""
        cache1 = get_manifest_cache()
        cache2 = get_manifest_cache()
        assert cache1 is cache2  # Singleton

    def test_clear_cache(self, tmp_path):
        """Test global clear function."""
        # Reset singleton for test
        import aparser_cli.manifest as mod
        mod._cache_instance = None

        cache = get_manifest_cache()
        cache.cache_path = tmp_path / "clear_test.json.gz"

        manifest = Manifest()
        cache.save(manifest)
        assert cache.cache_path.exists()

        clear_cache()
        assert mod._cache_instance is None

    def test_search_parsers_function(self):
        """Test search_parsers convenience function."""
        parser = ParserInfo(name="SE::Google", description="Google parser", category="SE")
        manifest = Manifest(parsers={"SE::Google": parser})

        results = search_parsers("Google", manifest=manifest)
        assert len(results) >= 1
