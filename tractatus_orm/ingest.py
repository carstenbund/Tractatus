from __future__ import annotations

from pathlib import Path

from .database import SessionLocal, init_db
from .models import Proposition
from .text_cleaner import extract_raw_propositions


def ingest_text(file_path: str | Path, language: str = "german") -> int:
    init_db()
    session = SessionLocal()
    lookup: dict[str, Proposition] = {}

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    entries = extract_raw_propositions(file_path, language=language)

    for idx, entry in enumerate(entries):
        level = entry.name.count(".") + 1
        proposition = Proposition(
            name=entry.name,
            text=entry.text,
            level=level,
            sort_order=idx,
        )
        lookup[entry.name] = proposition
        session.add(proposition)

    session.flush()

    for name, proposition in lookup.items():
        if "." not in name:
            continue
        parent_name = name.rsplit(".", 1)[0]
        parent = lookup.get(parent_name)
        if parent is not None:
            proposition.parent = parent

    session.commit()
    session.close()
    return len(lookup)


def main() -> None:
    raw_path = Path(__file__).resolve().parents[1] / "tractatus-raw.txt"
    print(raw_path)
    count = ingest_text(raw_path)
    print(f"Ingested {count} propositions from {raw_path.name}.")


if __name__ == "__main__":
    main()
