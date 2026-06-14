"""Tests for presets module."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from ayga_cli.presets import Preset, PresetManager, get_preset_manager, reset_preset_manager


class TestPreset:
    """Test Preset dataclass."""

    def test_basic_creation(self):
        """Test creating a basic preset."""
        preset = Preset(
            name="test-preset",
            parser="FreeAI::Perplexity",
            description="Test description",
            overrides={"proxyChecker": "reproxy_v4", "timeout": 120},
        )

        assert preset.name == "test-preset"
        assert preset.parser == "FreeAI::Perplexity"
        assert preset.description == "Test description"
        assert preset.overrides == {"proxyChecker": "reproxy_v4", "timeout": 120}

    def test_default_values(self):
        """Test preset with default values."""
        preset = Preset(name="minimal", parser="SE::Google")

        assert preset.name == "minimal"
        assert preset.parser == "SE::Google"
        assert preset.description == ""
        assert preset.overrides == {}

    def test_to_dict(self):
        """Test converting preset to dictionary."""
        preset = Preset(
            name="test",
            parser="FreeAI::Perplexity",
            description="Test",
            overrides={"timeout": 120},
        )

        data = preset.to_dict()

        assert data == {
            "parser": "FreeAI::Perplexity",
            "description": "Test",
            "overrides": {"timeout": 120},
        }

    def test_from_dict(self):
        """Test creating preset from dictionary."""
        data = {
            "parser": "FreeAI::Perplexity",
            "description": "Test description",
            "overrides": {"proxyChecker": "reproxy_v4"},
        }

        preset = Preset.from_dict("my-preset", data)

        assert preset.name == "my-preset"
        assert preset.parser == "FreeAI::Perplexity"
        assert preset.description == "Test description"
        assert preset.overrides == {"proxyChecker": "reproxy_v4"}

    def test_build_options(self):
        """Test converting overrides to options format."""
        preset = Preset(
            name="test",
            parser="SE::Google",
            overrides={"pagecount": 5, "timeout": 60},
        )

        options = preset.build_options()

        assert options == [
            {"id": "pagecount", "value": 5},
            {"id": "timeout", "value": 60},
        ]

    def test_build_options_empty(self):
        """Test build_options with empty overrides."""
        preset = Preset(name="test", parser="SE::Google")

        options = preset.build_options()

        assert options == []


class TestPresetManager:
    """Test PresetManager class."""

    def test_init_creates_directory(self):
        """Test that init creates config directory on save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            manager = PresetManager(config_dir)

            # Directory is created on first save, not init
            manager.save_preset(name="test", parser="SE::Google")

            assert config_dir.exists()
            assert manager.presets_path == config_dir / "presets.json"

    def test_save_and_load_preset(self):
        """Test saving and loading a preset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PresetManager(Path(tmpdir))

            preset = manager.save_preset(
                name="perplexity-test",
                parser="FreeAI::Perplexity",
                description="Test preset",
                overrides={"timeout": 120},
            )

            assert preset.name == "perplexity-test"
            assert manager.exists("perplexity-test")

            # Create new manager to test loading
            manager2 = PresetManager(Path(tmpdir))
            loaded = manager2.get_preset("perplexity-test")

            assert loaded is not None
            assert loaded.parser == "FreeAI::Perplexity"
            assert loaded.description == "Test preset"
            assert loaded.overrides == {"timeout": 120}

    def test_list_presets(self):
        """Test listing all presets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PresetManager(Path(tmpdir))

            manager.save_preset(name="preset-a", parser="SE::Google")
            manager.save_preset(name="preset-b", parser="FreeAI::Perplexity")
            manager.save_preset(name="preset-c", parser="Net::Whois")

            presets = manager.list_presets()

            assert len(presets) == 3
            # Should be sorted by name
            assert presets[0].name == "preset-a"
            assert presets[1].name == "preset-b"
            assert presets[2].name == "preset-c"

    def test_delete_preset(self):
        """Test deleting a preset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PresetManager(Path(tmpdir))

            manager.save_preset(name="to-delete", parser="SE::Google")
            assert manager.exists("to-delete")

            result = manager.delete_preset("to-delete")

            assert result is True
            assert not manager.exists("to-delete")

    def test_delete_nonexistent_preset(self):
        """Test deleting a preset that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PresetManager(Path(tmpdir))

            result = manager.delete_preset("nonexistent")

            assert result is False

    def test_update_existing_preset(self):
        """Test updating an existing preset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PresetManager(Path(tmpdir))

            manager.save_preset(name="test", parser="SE::Google", overrides={"pagecount": 1})
            manager.save_preset(name="test", parser="SE::Google", overrides={"pagecount": 10})

            preset = manager.get_preset("test")
            assert preset.overrides == {"pagecount": 10}

    def test_parse_overrides_string_key_value(self):
        """Test parsing key=value overrides string."""
        manager = PresetManager(Path(tempfile.gettempdir()))

        overrides = manager.parse_overrides_string("proxyChecker=reproxy_v4,timeout=120,pagecount=5")

        assert overrides == {
            "proxyChecker": "reproxy_v4",
            "timeout": 120,
            "pagecount": 5,
        }

    def test_parse_overrides_string_types(self):
        """Test that overrides string parsing handles types correctly."""
        manager = PresetManager(Path(tempfile.gettempdir()))

        overrides = manager.parse_overrides_string(
            "int_val=42,float_val=3.14,bool_true=true,bool_false=false,str_val=hello"
        )

        assert overrides["int_val"] == 42
        assert isinstance(overrides["int_val"], int)
        assert overrides["float_val"] == 3.14
        assert isinstance(overrides["float_val"], float)
        assert overrides["bool_true"] is True
        assert overrides["bool_false"] is False
        assert overrides["str_val"] == "hello"

    def test_parse_overrides_string_json(self):
        """Test parsing JSON overrides string."""
        manager = PresetManager(Path(tempfile.gettempdir()))

        overrides = manager.parse_overrides_string('{"proxyChecker": "reproxy_v4", "timeout": 120}')

        assert overrides == {
            "proxyChecker": "reproxy_v4",
            "timeout": 120,
        }

    def test_parse_overrides_string_empty(self):
        """Test parsing empty overrides string."""
        manager = PresetManager(Path(tempfile.gettempdir()))

        assert manager.parse_overrides_string("") == {}
        assert manager.parse_overrides_string(None) == {}

    def test_file_permissions(self):
        """Test that presets file has secure permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PresetManager(Path(tmpdir))
            manager.save_preset(name="test", parser="SE::Google")

            # Check file permissions (should be 0o600)
            stat = os.stat(manager.presets_path)
            # On Windows, this check might not apply
            if os.name != 'nt':
                assert stat.st_mode & 0o777 == 0o600


class TestGlobalPresetManager:
    """Test global preset manager functions."""

    def test_get_preset_manager_singleton(self):
        """Test that get_preset_manager returns singleton."""
        reset_preset_manager()

        manager1 = get_preset_manager()
        manager2 = get_preset_manager()

        assert manager1 is manager2

    def test_reset_preset_manager(self):
        """Test resetting global preset manager."""
        reset_preset_manager()

        manager1 = get_preset_manager()
        reset_preset_manager()
        manager2 = get_preset_manager()

        assert manager1 is not manager2
