from __future__ import annotations

import re
from pathlib import Path

from .database import SessionLocal, init_db
from .models import Proposition


LINE_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)")


def ingest_text(file_path: str | Path) -> int:
    init_db()
    session = SessionLocal()
    lookup: dict[str, Proposition] = {}

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    with file_path.open(encoding="utf-8") as handle:
        for idx, raw_line in enumerate(handle):
            line = raw_line.strip()
            if not line:
                continue
            match = LINE_RE.match(line)
            if not match:
                continue
            name, text = match.groups()
            level = name.count(".") + 1
            proposition = Proposition(
                name=name,
                text=text,
                level=level,
                sort_order=idx,
            )
            lookup[name] = proposition
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
    count = ingest_text(Path(__file__).resolve().parent / "tractatus.txt")
    print(f"Ingested {count} propositions.")


if __name__ == "__main__":
    main()
