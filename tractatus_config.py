"""Configuration and preferences management for Tractatus CLI and web application.

This module provides persistent user configuration storage using a JSON file
in the user's home directory (~/.trclirc). It manages display preferences,
language settings, and LLM parameters.

Configuration File:
    Location: ~/.trclirc
    Format: JSON
    Example:
        {
            "display_length": 100,
            "lines_per_output": 20,
            "lang": "en",
            "llm_max_tokens": 800,
            "tree_max_depth": 5
        }

The configuration is shared between the CLI and web interfaces, providing
a consistent experience across both modes of interaction.
"""

import json
from pathlib import Path
from typing import Any


class TrcliConfig:
    """Manages persistent user preferences with validation and defaults.

    This class handles loading, saving, and validating user configuration
    preferences. It provides type checking and range validation for all
    settings, with sensible defaults for new users.

    Preferences:
        display_length (int): Maximum characters to display in text snippets (1-1000)
        lines_per_output (int): Maximum lines for list/tree output (1-1000)
        lang (str): Default language code for translations ("de", "en", "fr", "pt")
        llm_max_tokens (int): Maximum tokens for LLM responses (10-4000)
        tree_max_depth (int): Maximum depth for tree traversal (0=unlimited, 1-12)

    Attributes:
        config_file: Path to the configuration file (~/.trclirc by default)
        preferences: Dictionary of current preference values
    """

    # Default preference values for new installations
    DEFAULT_PREFERENCES = {
        "display_length": 60,      # Characters to show in text previews
        "lines_per_output": 10,    # Max lines for list/tree commands
        "lang": "en",              # Default language (de=German, en=English, etc.)
        "llm_max_tokens": 500,     # Token budget for AI responses
        "tree_max_depth": 0,       # Tree depth limit (0=unlimited)
    }

    def __init__(self, config_file: str | Path | None = None):
        """Initialize configuration, loading from file if it exists.

        Args:
            config_file: Optional path to config file. Defaults to ~/.trclirc

        The constructor automatically loads existing preferences from the file,
        merging them with defaults. Invalid settings are ignored.
        """
        # Default to home directory if no custom path specified
        if config_file is None:
            config_file = Path.home() / ".trclirc"

        self.config_file = Path(config_file)
        # Start with default values
        self.preferences = self.DEFAULT_PREFERENCES.copy()
        # Override with saved preferences if they exist
        self.load()

    def load(self) -> None:
        """Load user preferences from the configuration file.

        Reads the JSON configuration file and merges saved preferences with
        defaults. Unknown keys are ignored to maintain forward compatibility.
        If the file doesn't exist or is malformed, falls back to defaults.

        The method is resilient to corruption - errors are logged but don't
        prevent the application from running with default settings.
        """

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    # Merge saved preferences with defaults (ignores unknown keys)
                    for key, value in data.items():
                        if key in self.DEFAULT_PREFERENCES:
                            self.preferences[key] = value
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with defaults
                print(f"Warning: Could not load config from {self.config_file}: {e}")

    def save(self) -> None:
        """Persist current preferences to the configuration file.

        Writes the current preferences to ~/.trclirc as formatted JSON.
        If the file doesn't exist, it will be created. Errors during save
        are logged but don't crash the application.
        """
        try:
            with open(self.config_file, "w") as f:
                # Pretty-print JSON for human readability
                json.dump(self.preferences, f, indent=2)
        except IOError as e:
            print(f"Error: Could not save config to {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a preference value by key.

        Args:
            key: Preference name (e.g., "lang", "display_length")
            default: Value to return if key not found (defaults to None)

        Returns:
            The preference value, or default if not found

        Example:
            config.get("lang")  # -> "en"
            config.get("unknown", "fallback")  # -> "fallback"
        """
        return self.preferences.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Update a preference value and save to disk.

        Args:
            key: Preference name (must be in DEFAULT_PREFERENCES)
            value: New value for the preference

        Returns:
            True if successful, False if key is invalid

        Note:
            This method does NOT validate the value. Use validate_preference()
            before calling set() if you need validation.

        Example:
            config.set("lang", "de")  # -> True
            config.set("unknown_key", "value")  # -> False
        """
        # Only allow setting known preferences
        if key not in self.DEFAULT_PREFERENCES:
            return False

        # Update in-memory preferences
        self.preferences[key] = value
        # Persist to disk
        self.save()
        return True

    def list_preferences(self) -> dict[str, Any]:
        """Return all current preferences."""
        return self.preferences.copy()

    def validate_preference(self, key: str, value: Any) -> tuple[bool, str]:
        """Validate a preference key and value before setting.

        Performs two levels of validation:
        1. Type checking: Ensures value matches the expected type
        2. Range checking: Ensures numeric values fall within valid ranges

        Args:
            key: Preference name to validate
            value: Proposed value for the preference

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passed, False otherwise
            - error_message: Empty string if valid, error description if invalid

        Validation Rules:
            - display_length: int, 1-1000 characters
            - lines_per_output: int, 1-1000 lines
            - lang: str, any value (no validation)
            - llm_max_tokens: int, 10-4000 tokens
            - tree_max_depth: int, 0-12 levels (0=unlimited)

        Example:
            is_valid, msg = config.validate_preference("display_length", 100)
            # -> (True, "")

            is_valid, msg = config.validate_preference("display_length", 5000)
            # -> (False, "display_length must be between 1 and 1000")
        """
        # Check if key exists
        if key not in self.DEFAULT_PREFERENCES:
            return False, f"Unknown preference: {key}"

        # Get expected type from default value
        default_value = self.DEFAULT_PREFERENCES[key]
        expected_type = type(default_value)

        # Type checking - ensure value is correct type
        if not isinstance(value, expected_type):
            return False, f"{key} must be {expected_type.__name__}, got {type(value).__name__}"

        # Range validation for numeric preferences
        if key == "display_length":
            if not (1 <= value <= 1000):
                return False, "display_length must be between 1 and 1000"
        elif key == "lines_per_output":
            if not (1 <= value <= 1000):
                return False, "lines_per_output must be between 1 and 1000"
        elif key == "llm_max_tokens":
            if not (10 <= value <= 4000):
                return False, "llm_max_tokens must be between 10 and 4000"
        elif key == "tree_max_depth":
            if not (0 <= value <= 12):
                return False, "tree_max_depth must be between 0 and 12"
        # Note: "lang" (string) has no range validation

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
