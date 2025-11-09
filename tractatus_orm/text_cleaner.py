"""Utilities for extracting structured propositions from the raw Tractatus text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


PROPOSITION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)")


@dataclass(frozen=True)
class PropositionEntry:
    """Structured representation of a Tractatus proposition."""

    name: str
    text: str


def _is_page_marker(line: str) -> bool:
    return line.isdigit() and int(line) > 7


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace("\xad", "").strip())


def extract_german_propositions(raw_path: Path) -> list[PropositionEntry]:
    """Extract Tractatus propositions from the German section of the raw text."""

    raw_text = raw_path.read_text(encoding="utf-8")
    marker = "Logisch-Philosophische Abhandlung"
    if marker not in raw_text:
        raise ValueError("German section not found in raw text")

    german_section = raw_text.split(marker, 1)[1]

    entries: list[PropositionEntry] = []
    seen: set[str] = set()
    for raw_line in german_section.splitlines():
        line = raw_line.strip()
        if not line or _is_page_marker(line):
            continue
        match = PROPOSITION_RE.match(line)
        if not match:
            continue
        name, text = match.groups()
        if name in seen:
            continue
        seen.add(name)
        entries.append(PropositionEntry(name=name, text=_clean_line(text)))

    if not entries:
        raise ValueError("Failed to extract German propositions")

    return entries


def extract_raw_propositions(raw_path: Path, language: str = "german") -> list[PropositionEntry]:
    language = language.lower()
    if language != "german":
        raise ValueError("Only German extraction is supported at present")
    return extract_german_propositions(raw_path)

