"""Presets management for ayga_parser CLI.

Provides a system for saving and loading parser presets with override configurations.
Presets are stored in ~/.config/ayga-cli/presets.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class Preset:
    """A parser preset with saved configuration overrides.

    Attributes:
        name: Unique preset identifier
        parser: Parser name (e.g., "FreeAI::Perplexity")
        description: Human-readable description
        overrides: Dictionary of option overrides
    """

    name: str
    parser: str
    description: str = ""
    overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert preset to dictionary format."""
        return {
            "parser": self.parser,
            "description": self.description,
            "overrides": self.overrides,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Preset":
        """Create preset from dictionary format."""
        return cls(
            name=name,
            parser=data.get("parser", ""),
            description=data.get("description", ""),
            overrides=data.get("overrides", {}),
        )

    def build_options(self) -> list[dict[str, Any]]:
        """Convert overrides to ayga_parser options format.

        Returns:
            List of option dictionaries for API calls
        """
        return [{"id": k, "value": v} for k, v in self.overrides.items()]


class PresetManager:
    """Manages preset storage and retrieval.

    Presets are stored in JSON format at ~/.config/ayga-cli/presets.json
    with file permissions set to 600 (owner read/write only).
    """

    PRESETS_FILENAME = "presets.json"

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize preset manager.

        Args:
            config_dir: Optional custom config directory path
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "ayga-cli"
        self.config_dir = config_dir
        self.presets_path = self.config_dir / self.PRESETS_FILENAME
        self._presets: dict[str, Preset] = {}
        self._load()

    def _load(self) -> None:
        """Load presets from storage file."""
        if not self.presets_path.exists():
            self._presets = {}
            return

        try:
            with open(self.presets_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._presets = {
                name: Preset.from_dict(name, preset_data)
                for name, preset_data in data.items()
            }
        except (json.JSONDecodeError, IOError):
            self._presets = {}

    def _save(self) -> None:
        """Save presets to storage file."""
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Convert to storage format
        data = {
            name: preset.to_dict()
            for name, preset in self._presets.items()
        }

        # Write with secure permissions
        with open(self.presets_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Set secure permissions (owner read/write only)
        os.chmod(self.presets_path, 0o600)

    def list_presets(self) -> list[Preset]:
        """Get list of all stored presets.

        Returns:
            List of Preset objects sorted by name
        """
        return sorted(self._presets.values(), key=lambda p: p.name)

    def get_preset(self, name: str) -> Optional[Preset]:
        """Get a preset by name.

        Args:
            name: Preset name

        Returns:
            Preset if found, None otherwise
        """
        return self._presets.get(name)

    def save_preset(
        self,
        name: str,
        parser: str,
        description: str = "",
        overrides: Optional[dict[str, Any]] = None,
    ) -> Preset:
        """Save or update a preset.

        Args:
            name: Unique preset identifier
            parser: Parser name
            description: Human-readable description
            overrides: Dictionary of option overrides

        Returns:
            The saved Preset object
        """
        preset = Preset(
            name=name,
            parser=parser,
            description=description,
            overrides=overrides or {},
        )
        self._presets[name] = preset
        self._save()
        return preset

    def delete_preset(self, name: str) -> bool:
        """Delete a preset.

        Args:
            name: Preset name to delete

        Returns:
            True if preset was deleted, False if not found
        """
        if name in self._presets:
            del self._presets[name]
            self._save()
            return True
        return False

    def exists(self, name: str) -> bool:
        """Check if a preset exists.

        Args:
            name: Preset name to check

        Returns:
            True if preset exists
        """
        return name in self._presets

    def parse_overrides_string(self, overrides_str: str) -> dict[str, Any]:
        """Parse overrides string into dictionary.

        Supports formats:
        - key=value,key2=value2 (comma-separated pairs)
        - JSON object string

        Args:
            overrides_str: Overrides as string

        Returns:
            Dictionary of overrides

        Examples:
            >>> pm.parse_overrides_string("proxyChecker=reproxy_v4,timeout=120")
            {'proxyChecker': 'reproxy_v4', 'timeout': 120}
        """
        if not overrides_str:
            return {}

        # Try JSON first
        try:
            data = json.loads(overrides_str)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Parse key=value pairs
        overrides = {}
        for pair in overrides_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Try to convert value to appropriate type
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        # Handle booleans
                        if value.lower() == "true":
                            value = True
                        elif value.lower() == "false":
                            value = False

                overrides[key] = value

        return overrides


# Global preset manager instance
_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    """Get global preset manager instance.

    Returns:
        PresetManager singleton instance
    """
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager


def reset_preset_manager() -> None:
    """Reset global preset manager (mainly for testing)."""
    global _preset_manager
    _preset_manager = None
