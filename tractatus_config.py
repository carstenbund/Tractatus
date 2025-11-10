"""Configuration and preferences management for Tractatus CLI."""

import json
from pathlib import Path
from typing import Any


class TrcliConfig:
    """Manages user preferences stored in .trclirc file."""

    DEFAULT_PREFERENCES = {
        "display_length": 60,  # Characters to display for text snippets
        "lines_per_output": 10,  # Max lines to display for list/tree output
        "lang": "en",  # Default language for translations
        "llm_max_tokens": 500,  # Max tokens for LLM responses
    }

    def __init__(self, config_file: str | Path | None = None):
        """Initialize configuration from file or defaults."""
        if config_file is None:
            config_file = Path.home() / ".trclirc"
        self.config_file = Path(config_file)
        self.preferences = self.DEFAULT_PREFERENCES.copy()
        self.load()

    def load(self) -> None:
        """Load preferences from .trclirc file if it exists."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    # Validate and merge with defaults
                    for key, value in data.items():
                        if key in self.DEFAULT_PREFERENCES:
                            self.preferences[key] = value
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config from {self.config_file}: {e}")

    def save(self) -> None:
        """Save preferences to .trclirc file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.preferences, f, indent=2)
        except IOError as e:
            print(f"Error: Could not save config to {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self.preferences.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Set a preference value.

        Returns True if successful, False if key is invalid.
        """
        if key not in self.DEFAULT_PREFERENCES:
            return False
        self.preferences[key] = value
        self.save()
        return True

    def list_preferences(self) -> dict[str, Any]:
        """Return all current preferences."""
        return self.preferences.copy()

    def validate_preference(self, key: str, value: Any) -> tuple[bool, str]:
        """
        Validate a preference value.

        Returns (is_valid, error_message).
        """
        if key not in self.DEFAULT_PREFERENCES:
            return False, f"Unknown preference: {key}"

        default_value = self.DEFAULT_PREFERENCES[key]
        expected_type = type(default_value)

        # Type checking
        if not isinstance(value, expected_type):
            return False, f"{key} must be {expected_type.__name__}, got {type(value).__name__}"

        # Value-specific validation
        if key == "display_length":
            if not (1 <= value <= 1000):
                return False, "display_length must be between 1 and 1000"
        elif key == "lines_per_output":
            if not (1 <= value <= 1000):
                return False, "lines_per_output must be between 1 and 1000"
        elif key == "llm_max_tokens":
            if not (10 <= value <= 4000):
                return False, "llm_max_tokens must be between 10 and 4000"

        return True, ""

    def reset(self, key: str | None = None) -> bool:
        """Reset preference(s) to default. If key is None, reset all."""
        if key is None:
            self.preferences = self.DEFAULT_PREFERENCES.copy()
            self.save()
            return True

        if key not in self.DEFAULT_PREFERENCES:
            return False

        self.preferences[key] = self.DEFAULT_PREFERENCES[key]
        self.save()
        return True
