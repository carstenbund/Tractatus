"""SQLite-backed cache for agent responses.

The cache is stored in the system temporary directory and is therefore
considered ephemeral. It is primarily used to avoid repeated calls to the
configured LLM backend when identical prompts are requested.
"""

from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Optional


class AgentCache:
    """Persist LLM responses for reuse across CLI and web sessions."""

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS agent_cache (
        prompt_hash TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        prompt TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """

    def __init__(self, path: str | Path | None = None) -> None:
        temp_dir = Path(tempfile.gettempdir())
        self.path = Path(path) if path is not None else temp_dir / "tractatus_agent_cache.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialise()

    def lookup(self, action: str, prompt: str) -> Optional[str]:
        """Return cached response text for the supplied action + prompt."""

        cache_key = self._hash_key(action, prompt)
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT content FROM agent_cache WHERE prompt_hash = ?",
                    (cache_key,),
                ).fetchone()
        if row:
            return row[0]
        return None

    def store(self, action: str, prompt: str, content: str) -> None:
        """Persist the generated content for future reuse."""

        cache_key = self._hash_key(action, prompt)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_cache
                    (prompt_hash, action, prompt, content)
                    VALUES (?, ?, ?, ?)
                    """,
                    (cache_key, action, prompt, content),
                )
                conn.commit()

    def _initialise(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(self._CREATE_TABLE)
                conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, check_same_thread=False)

    @staticmethod
    def _hash_key(action: str, prompt: str) -> str:
        digest = hashlib.sha256()
        digest.update(action.encode("utf-8"))
        digest.update(b"\0")
        digest.update(prompt.encode("utf-8"))
        return digest.hexdigest()


_DEFAULT_CACHE: AgentCache | None = None


def get_default_cache() -> AgentCache:
    """Return a process-wide cache instance."""

    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = AgentCache()
    return _DEFAULT_CACHE

