"""Manifest cache and fuzzy search for ayga_parser parsers.

This module provides:
- ManifestCache: Manages local cache of ayga_parser manifest with TTL
- FuzzySearchIndex: Inverted index for fuzzy parser search
- Manifest models: Pydantic models for manifest data structures
- StaticManifest: Loads static manifest for offline parser reference
"""

from __future__ import annotations

import gzip
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

# Import new static manifest module
from ayga_cli.static_manifest import (
    ParserDefaults,
    STATIC_PARSERS,
    get_parser_defaults,
    list_parsers,
    get_all_categories,
)


# =============================================================================
# Static Manifest (Legacy - now delegates to static_manifest module)
# =============================================================================

class StaticManifest:
    """Loads and provides access to static parser manifest.

    The static manifest contains pre-defined information about popular parsers
    without requiring an API call. Useful for offline reference and documentation.

    Note: This class now delegates to the static_manifest module for data.
    """

    _instance: Optional["StaticManifest"] = None

    def __new__(cls) -> "StaticManifest":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    @property
    def version(self) -> str:
        """Return static manifest version."""
        return "2.2.0"

    def _load(self) -> None:
        """Legacy method - no longer needed."""
        pass

    def get_parser(self, name: str) -> Optional[dict]:
        """Get parser info by name from static manifest.

        Args:
            name: Parser name (e.g., 'FreeAI::Perplexity')

        Returns:
            Parser dict if found, None otherwise
        """
        defaults = get_parser_defaults(name)
        if defaults:
            return {
                "name": defaults.parser,
                "description": defaults.description,
                "category": defaults.category,
                "required_overrides": defaults.required_overrides,
                "default_overrides": defaults.default_overrides,
                "examples": defaults.examples,
                "notes": defaults.notes,
            }
        return None

    def get_all_parsers(self) -> dict[str, dict]:
        """Get all parsers from static manifest.

        Returns:
            Dict of parser name -> parser info
        """
        return {
            name: {
                "name": p.parser,
                "description": p.description,
                "category": p.category,
                "required_overrides": p.required_overrides,
                "default_overrides": p.default_overrides,
                "examples": p.examples,
                "notes": p.notes,
            }
            for name, p in STATIC_PARSERS.items()
        }

    def get_parsers_by_category(self, category: str) -> list[dict]:
        """Get all parsers in a category.

        Args:
            category: Category name (e.g., 'FreeAI', 'SE')

        Returns:
            List of parser dicts
        """
        parsers = list_parsers(category=category)
        return [
            {
                "name": p.parser,
                "description": p.description,
                "category": p.category,
                "required_overrides": p.required_overrides,
                "default_overrides": p.default_overrides,
                "examples": p.examples,
                "notes": p.notes,
            }
            for p in parsers
        ]

    def get_categories(self) -> list[str]:
        """Get all unique categories.

        Returns:
            Sorted list of category names
        """
        return get_all_categories()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Simple search in static manifest.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching parser dicts
        """
        query_lower = query.lower()
        matches = []

        for name, info in self.get_all_parsers().items():
            score = 0.0

            # Exact match
            if name.lower() == query_lower:
                score = 1.0
            # Name contains query
            elif query_lower in name.lower():
                score = 0.8
            # Description contains query
            elif query_lower in info.get("description", "").lower():
                score = 0.5
            # Keywords match
            else:
                for keyword in info.get("keywords", []):
                    if query_lower in keyword.lower():
                        score = 0.4
                        break

            if score > 0:
                matches.append((score, info))

        # Sort by score and return top matches
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:limit]]

    @property
    def version(self) -> str:
        """Get manifest version."""
        return "2.2.0"

    @property
    def parser_count(self) -> int:
        """Get total parser count."""
        return len(self.get_all_parsers())


# =============================================================================
# Utility Functions
# =============================================================================


def _split_camel_case(text: str) -> list[str]:
    """Split camelCase or PascalCase text into words."""
    # Insert space before capital letters
    spaced = re.sub(r"([A-Z])", r" \1", text).strip()
    return spaced.lower().split()


def _extract_category(name: str) -> str:
    """Extract category from parser name."""
    if "::" in name:
        return name.split("::")[0]
    return "Other"


def _build_keywords(name: str, description: str) -> list[str]:
    """Build keywords from name and description."""
    keywords = set()

    # Add name parts
    if name:
        keywords.add(name.lower())
        if "::" in name:
            parts = name.split("::")
            keywords.add(parts[0].lower())
            keywords.add(parts[1].lower())
            # Add camelCase split
            keywords.update(_split_camel_case(parts[1]))

    # Add words from description
    if description:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", description.lower())
        keywords.update(words)

    return sorted(list(keywords))


# =============================================================================
# Manifest Models
# =============================================================================


class ParameterSchema(BaseModel):
    """Schema for a parser parameter."""

    type: str = Field(default="string", description="Parameter type (string, integer, float, boolean)")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value")
    min: Optional[float] = Field(default=None, description="Minimum value for numbers")
    max: Optional[float] = Field(default=None, description="Maximum value for numbers")
    enum: Optional[list[str]] = Field(default=None, description="Allowed values for enum type")


class ParserInfo(BaseModel):
    """Complete information about a parser."""

    name: str = Field(..., description="Parser name (e.g., 'SE::Google')")
    description: str = Field(default="", description="Human-readable description")
    category: str = Field(default="", description="Parser category (e.g., 'SE', 'FreeAI')")
    keywords: list[str] = Field(default_factory=list, description="Keywords for search")
    presets: list[str] = Field(default_factory=list, description="Available preset names")
    parameters: dict[str, ParameterSchema] = Field(
        default_factory=dict, description="Parameter schemas"
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to set derived fields."""
        # Set category if not provided
        if not self.category:
            self.category = _extract_category(self.name)
        # Set keywords if not provided
        if not self.keywords:
            self.keywords = _build_keywords(self.name, self.description)


class Manifest(BaseModel):
    """Complete manifest of all ayga_parser parsers."""

    version: str = Field(default="2.1.0", description="Manifest schema version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parser_count: int = Field(default=0, description="Total number of parsers")
    parsers: dict[str, ParserInfo] = Field(
        default_factory=dict, description="Parser info keyed by name"
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to set derived fields."""
        # Set parser_count from parsers dict
        if not self.parser_count:
            self.parser_count = len(self.parsers)

    def get_parser(self, name: str) -> Optional[ParserInfo]:
        """Get parser info by exact name."""
        return self.parsers.get(name)

    def get_parsers_by_category(self, category: str) -> list[ParserInfo]:
        """Get all parsers in a category."""
        return [p for p in self.parsers.values() if p.category == category]

    def get_categories(self) -> list[str]:
        """Get all unique categories."""
        return sorted(list(set(p.category for p in self.parsers.values())))


# =============================================================================
# Cache Management
# =============================================================================


class ManifestCache:
    """Manages local cache of ayga_parser manifest.

    The cache is stored as a compressed JSON file at ~/.config/ayga-cli/manifest.json.gz
    with file permissions set to 600 (owner read/write only).

    Attributes:
        config: AygaParserConfig instance
        cache_path: Path to the cache file
        ttl_hours: Time-to-live in hours (default: 24)
    """

    DEFAULT_TTL_HOURS = 24
    CACHE_FILENAME = "manifest.json.gz"
    MANIFEST_VERSION = "2.1.0"

    def __init__(
        self,
        config: Optional[Any] = None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        # Delay import to avoid circular dependency
        if config is None:
            from ayga_cli.config import get_config
            self.config = get_config()
        else:
            self.config = config
        self.ttl_hours = ttl_hours
        self.cache_path = self._get_cache_path()
        self._manifest: Optional[Manifest] = None

    def _get_cache_path(self) -> Path:
        """Get the path to the cache file."""
        config_dir = self.config.get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / self.CACHE_FILENAME

    def exists(self) -> bool:
        """Check if cache file exists."""
        return self.cache_path.exists()

    def is_expired(self) -> bool:
        """Check if cache is older than TTL."""
        if not self.exists():
            return True

        try:
            stat = self.cache_path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            age = datetime.now(timezone.utc) - modified
            return age > timedelta(hours=self.ttl_hours)
        except (OSError, ValueError):
            return True

    def is_corrupted(self) -> bool:
        """Check if cache file is corrupted (invalid JSON or structure)."""
        if not self.exists():
            return False

        try:
            with gzip.open(self.cache_path, "rt", encoding="utf-8") as f:
                data = json.load(f)

            # Validate required fields
            if not isinstance(data, dict):
                return True
            if "version" not in data or "parsers" not in data:
                return True

            # Try to parse as Manifest
            Manifest.model_validate(data)
            return False
        except (OSError, gzip.BadGzipFile, json.JSONDecodeError, Exception):
            return True

    def get_age_hours(self) -> float:
        """Get cache age in hours."""
        if not self.exists():
            return float("inf")

        try:
            stat = self.cache_path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            age = datetime.now(timezone.utc) - modified
            return age.total_seconds() / 3600
        except (OSError, ValueError):
            return float("inf")

    def load(self) -> Optional[Manifest]:
        """Load manifest from cache.

        Returns:
            Manifest if cache exists and is valid, None otherwise.
        """
        if self._manifest is not None:
            return self._manifest

        if not self.exists() or self.is_corrupted():
            return None

        try:
            with gzip.open(self.cache_path, "rt", encoding="utf-8") as f:
                data = json.load(f)

            self._manifest = Manifest.model_validate(data)
            return self._manifest
        except Exception:
            return None

    def save(self, manifest: Manifest) -> None:
        """Save manifest to cache.

        Args:
            manifest: Manifest to save
        """
        # Ensure directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to JSON
        data = manifest.model_dump(mode="json")

        # Write with compression
        with gzip.open(self.cache_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Set secure permissions (owner read/write only)
        os.chmod(self.cache_path, 0o600)

        self._manifest = manifest

    def clear(self) -> None:
        """Clear the cache file."""
        if self.cache_path.exists():
            self.cache_path.unlink()
        self._manifest = None

    async def sync(
        self,
        force: bool = False,
        verbose: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> Manifest:
        """Fetch all parsers from API and save to cache.

        Args:
            force: Bypass TTL check and force refresh
            verbose: Print progress information
            progress_callback: Optional callback(current, total, parser_name)

        Returns:
            Updated Manifest

        Raises:
            AygaParserAPIError: If API calls fail
            AygaParserAuthError: If authentication fails
        """
        # Delay import to avoid circular dependency
        from ayga_cli.client.http import AygaParserHttpClient

        # Check if sync is needed
        if not force and not self.is_expired() and not self.is_corrupted():
            manifest = self.load()
            if manifest:
                if verbose:
                    print(f"Cache is fresh ({self.get_age_hours():.1f}h old). Skipping sync.")
                return manifest

        if verbose:
            print("Syncing parser manifest from ayga_parser API...")

        # Fetch from API
        async with AygaParserHttpClient(self.config) as client:
            # Get list of all parsers
            parser_names = await client.get_parsers_list()

            if not parser_names:
                raise ValueError("No parsers returned from API")

            if verbose:
                print(f"Found {len(parser_names)} parsers. Fetching details...")

            # Fetch details for each parser
            parsers: dict[str, ParserInfo] = {}
            total = len(parser_names)

            for i, name in enumerate(parser_names):
                parser_name = name.get("name") if isinstance(name, dict) else str(name)
                if verbose and progress_callback:
                    progress_callback(i + 1, total, parser_name)
                elif verbose and (i + 1) % 10 == 0:
                    print(f"  Progress: {i + 1}/{total} parsers...")

                try:
                    info_data = await client.get_parser_info(parser_name)
                    parser_info = self._convert_api_info_to_parser_info(parser_name, info_data)
                    parsers[parser_name] = parser_info
                except Exception as e:
                    static_defaults = get_parser_defaults(parser_name)
                    if static_defaults:
                        parsers[parser_name] = self._convert_static_defaults_to_parser_info(static_defaults)
                        if verbose:
                            print(f"  Warning: Falling back to static manifest for {parser_name}: {e}")
                        continue
                    if verbose:
                        print(f"  Warning: Failed to fetch info for {parser_name}: {e}")
                    # Continue with other parsers

            if verbose:
                print(f"Successfully fetched {len(parsers)}/{total} parsers")

        # Build and save manifest
        manifest = Manifest(
            version=self.MANIFEST_VERSION,
            created_at=datetime.now(timezone.utc),
            parser_count=len(parsers),
            parsers=parsers,
        )

        self.save(manifest)

        if verbose:
            print(f"Manifest saved to {self.cache_path}")

        return manifest

    def _convert_api_info_to_parser_info(
        self, name: str, api_data: dict
    ) -> ParserInfo:
        """Convert API response to ParserInfo model.

        Args:
            name: Parser name
            api_data: Raw API response data

        Returns:
            ParserInfo instance
        """
        # Extract description
        description = api_data.get("description", "")
        if not description:
            description = api_data.get("desc", "")

        # Extract category
        category = api_data.get("category", "")
        if not category and "::" in name:
            category = name.split("::")[0]

        # Extract presets
        presets = api_data.get("presets", [])
        if not presets:
            # Try to extract from options
            options = api_data.get("options", [])
            for opt in options:
                if isinstance(opt, dict) and opt.get("id") == "preset":
                    values = opt.get("values", [])
                    if values:
                        presets = values
                    break
        if not presets:
            presets = ["default"]

        # Extract parameters
        parameters: dict[str, ParameterSchema] = {}
        options = api_data.get("options", [])
        for opt in options:
            if not isinstance(opt, dict):
                continue

            param_id = opt.get("id", "")
            if not param_id or param_id == "preset":
                continue

            param_type = self._convert_api_type(opt.get("type", "string"))
            param_schema = ParameterSchema(
                type=param_type,
                description=opt.get("label", opt.get("description", "")),
                required=opt.get("required", False),
                default=opt.get("default"),
            )

            # Add min/max for numeric types
            if param_type in ("integer", "float"):
                if "min" in opt:
                    param_schema.min = opt["min"]
                if "max" in opt:
                    param_schema.max = opt["max"]

            # Add enum values
            if "values" in opt and isinstance(opt["values"], list):
                param_schema.enum = [str(v) for v in opt["values"]]

            parameters[param_id] = param_schema

        return ParserInfo(
            name=name,
            description=description,
            category=category,
            keywords=[],  # Will be auto-generated from name and description
            presets=presets,
            parameters=parameters,
        )

    def _convert_static_defaults_to_parser_info(self, defaults: ParserDefaults) -> ParserInfo:
        """Convert static manifest defaults into a ParserInfo model."""
        parameters: dict[str, ParameterSchema] = {}
        for option_name, value in defaults.default_overrides.items():
            option_type = "boolean" if isinstance(value, bool) else "integer" if isinstance(value, int) and not isinstance(value, bool) else "float" if isinstance(value, float) else "string"
            parameters[option_name] = ParameterSchema(
                type=option_type,
                description="Static manifest default option",
                required=option_name in defaults.required_overrides,
                default=value,
            )

        for option_name in defaults.required_overrides:
            parameters.setdefault(
                option_name,
                ParameterSchema(
                    type="string",
                    description="Required option from static manifest",
                    required=True,
                ),
            )

        return ParserInfo(
            name=defaults.parser,
            description=defaults.description,
            category=defaults.category,
            presets=["default"],
            parameters=parameters,
        )

    def _convert_api_type(self, api_type: str) -> str:
        """Convert API type to standard type name."""
        type_map = {
            "int": "integer",
            "integer": "integer",
            "float": "float",
            "double": "float",
            "number": "float",
            "bool": "boolean",
            "boolean": "boolean",
            "checkbox": "boolean",
            "string": "string",
            "text": "string",
            "textarea": "string",
            "select": "string",
            "enum": "string",
        }
        return type_map.get(api_type.lower(), "string")


# =============================================================================
# Fuzzy Search
# =============================================================================


@dataclass
class ParserMatch:
    """Result of a fuzzy search match."""

    parser: ParserInfo
    score: float = 0.0
    match_type: str = ""  # exact, prefix, substring, fuzzy, keyword
    matched_term: str = ""


class FuzzySearchIndex:
    """Inverted index for fuzzy parser search.

    Provides fast fuzzy matching with ranking by relevance.
    Match types (in order of priority):
    1. Exact match (name == query)
    2. Prefix match (name starts with query)
    3. Substring match (name contains query)
    4. Keyword match (keywords contain query)
    5. Fuzzy match (Levenshtein distance <= 2)
    """

    def __init__(self, manifest: Optional[Manifest] = None):
        self.manifest = manifest
        self._index: dict[str, set[str]] = {}  # keyword -> set of parser names
        self._built = False

    def build(self, manifest: Manifest) -> None:
        """Build index from manifest.

        Args:
            manifest: Manifest to index
        """
        self.manifest = manifest
        self._index = {}

        for name, parser in manifest.parsers.items():
            # Index the full name
            self._add_to_index(name.lower(), name)

            # Index category
            if parser.category:
                self._add_to_index(parser.category.lower(), name)

            # Index keywords
            for keyword in parser.keywords:
                self._add_to_index(keyword.lower(), name)

            # Index description words
            if parser.description:
                words = re.findall(r"\b[a-zA-Z]{3,}\b", parser.description.lower())
                for word in words:
                    self._add_to_index(word, name)

            # Index name parts (for SE::Google style)
            if "::" in name:
                parts = name.split("::")
                self._add_to_index(parts[0].lower(), name)
                self._add_to_index(parts[1].lower(), name)
                # Index camelCase splits
                for part in _split_camel_case(parts[1]):
                    self._add_to_index(part, name)

        self._built = True

    def _add_to_index(self, term: str, parser_name: str) -> None:
        """Add a term to the index."""
        if term not in self._index:
            self._index[term] = set()
        self._index[term].add(parser_name)

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.3,
        category: Optional[str] = None,
    ) -> list[ParserMatch]:
        """Fuzzy search for parsers.

        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum confidence score (0.0-1.0)
            category: Optional category filter

        Returns:
            List of ParserMatch objects sorted by relevance
        """
        if not self._built or not self.manifest:
            return []

        query_lower = query.lower().strip()
        if not query_lower:
            return []

        matches: dict[str, ParserMatch] = {}

        # Check each parser
        for name, parser in self.manifest.parsers.items():
            # Category filter
            if category and parser.category != category:
                continue

            score, match_type, matched_term = self._calculate_score(
                query_lower, name, parser
            )

            if score >= min_score:
                matches[name] = ParserMatch(
                    parser=parser,
                    score=score,
                    match_type=match_type,
                    matched_term=matched_term,
                )

        # Sort by score descending, then by name
        sorted_matches = sorted(
            matches.values(),
            key=lambda m: (-m.score, m.parser.name),
        )

        return sorted_matches[:limit]

    def _calculate_score(
        self, query: str, name: str, parser: ParserInfo
    ) -> tuple[float, str, str]:
        """Calculate match score for a parser.

        Returns:
            Tuple of (score, match_type, matched_term)
        """
        name_lower = name.lower()

        # 1. Exact match (highest priority)
        if name_lower == query:
            return 1.0, "exact", name

        # 2. Prefix match
        if name_lower.startswith(query):
            return 0.9, "prefix", name

        # 3. Substring match in name
        if query in name_lower:
            return 0.8, "substring", name

        # 4. Keyword match
        for keyword in parser.keywords:
            if query == keyword.lower():
                return 0.7, "keyword", keyword
            if query in keyword.lower():
                return 0.6, "keyword", keyword

        # 5. Index lookup
        if query in self._index:
            if name in self._index[query]:
                return 0.65, "keyword", query

        # 6. Fuzzy match (Levenshtein distance) on name parts
        # Check against the short name (after ::)
        if "::" in name:
            short_name = name.split("::")[1].lower()
            distance = self._levenshtein_distance(query, short_name)
            if distance <= 2:
                score = max(0.3, 0.5 - (distance * 0.1))
                return score, "fuzzy", name

        # Check against full name
        distance = self._levenshtein_distance(query, name_lower)
        if distance <= 2:
            score = max(0.3, 0.5 - (distance * 0.1))
            return score, "fuzzy", name

        # 7. Fuzzy match on keywords
        for keyword in parser.keywords:
            distance = self._levenshtein_distance(query, keyword.lower())
            if distance <= 2:
                score = max(0.3, 0.45 - (distance * 0.1))
                return score, "fuzzy_keyword", keyword

        return 0.0, "", ""

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost is 0 if characters match, 1 otherwise
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


# =============================================================================
# Convenience Functions
# =============================================================================


async def get_manifest(
    force_sync: bool = False,
    verbose: bool = False,
) -> Optional[Manifest]:
    """Get manifest, syncing if necessary.

    Args:
        force_sync: Force a sync even if cache is fresh
        verbose: Print progress information

    Returns:
        Manifest if available, None otherwise
    """
    cache = ManifestCache()

    # Try to load from cache first
    if not force_sync:
        manifest = cache.load()
        if manifest:
            return manifest

    # Sync from API
    try:
        return await cache.sync(force=force_sync, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"Failed to sync manifest: {e}")
        # Return stale cache if available
        manifest = cache.load()
        if manifest:
            return manifest

        static = StaticManifest()
        static_parsers = {
            name: cache._convert_static_defaults_to_parser_info(defaults)
            for name, defaults in STATIC_PARSERS.items()
        }
        return Manifest(
            version=static.version,
            parser_count=len(static_parsers),
            parsers=static_parsers,
        )


def search_parsers(
    query: str,
    manifest: Optional[Manifest] = None,
    limit: int = 10,
    min_score: float = 0.3,
    category: Optional[str] = None,
) -> list[ParserMatch]:
    """Search parsers using fuzzy matching.

    Args:
        query: Search query
        manifest: Optional manifest (loads from cache if not provided)
        limit: Maximum results
        min_score: Minimum confidence score
        category: Optional category filter

    Returns:
        List of matching parsers
    """
    if manifest is None:
        cache = ManifestCache()
        manifest = cache.load()

    if not manifest:
        return []

    index = FuzzySearchIndex(manifest)
    index.build(manifest)

    return index.search(query, limit=limit, min_score=min_score, category=category)


# =============================================================================
# Backward Compatibility (for MCP server transition)
# =============================================================================


class FuzzySearchEngine:
    """Backward-compatible wrapper for FuzzySearchIndex.
    
    This class provides the old API used by the MCP server.
    TODO: Update MCP server to use FuzzySearchIndex directly.
    """

    def __init__(self):
        self._index: Optional[FuzzySearchIndex] = None
        self._manifest: Optional[Manifest] = None
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load manifest from cache."""
        cache = ManifestCache()
        self._manifest = cache.load()
        if self._manifest:
            self._index = FuzzySearchIndex(self._manifest)
            self._index.build(self._manifest)

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.5,
    ) -> list[dict]:
        """Search parsers and return results in old format.
        
        Returns:
            List of dicts with 'name', 'description', 'category', 'confidence' keys
        """
        if not self._index:
            return []

        matches = self._index.search(
            query=query,
            limit=limit,
            min_score=min_confidence,
        )

        return [
            {
                "name": m.parser.name,
                "description": m.parser.description,
                "category": m.parser.category,
                "confidence": round(m.score, 2),
                "match_type": m.match_type,
            }
            for m in matches
        ]


def get_fuzzy_engine() -> FuzzySearchEngine:
    """Get a fuzzy search engine instance (backward compatibility)."""
    return FuzzySearchEngine()


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Aliases for backward compatibility
ParserParameter = ParameterSchema


# Global cache instance for singleton pattern
_cache_instance: Optional[ManifestCache] = None


def get_manifest_cache(config: Optional[Any] = None) -> ManifestCache:
    """Get global manifest cache instance.

    Args:
        config: Optional config override

    Returns:
        ManifestCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ManifestCache(config)
    return _cache_instance


def clear_cache() -> None:
    """Clear the manifest cache (backward compatibility)."""
    global _cache_instance
    if _cache_instance:
        _cache_instance.clear()
    _cache_instance = None


def get_fuzzy_engine(config: Optional[Any] = None) -> FuzzySearchEngine:
    """Get fuzzy search engine instance (backward compatibility).

    Args:
        config: Optional config override

    Returns:
        FuzzySearchEngine instance
    """
    return FuzzySearchEngine()
