from pathlib import Path
import xml.etree.ElementTree as ET
from .database import SessionLocal, init_db
from .models import Proposition, Translation

def ingest_multilang_xml(file_path: str | Path) -> int:
    init_db()
    session = SessionLocal()
    lookup: dict[str, Proposition] = {}

    tree = ET.parse(file_path)
    root = tree.getroot()
    rows = root.findall(".//proposition")

    # --- 1. create propositions (with German text as base) ---
    for idx, prop in enumerate(rows):
        name = prop.get("id")
        if not name:
            continue
        level = int(prop.get("depth", "1"))
        german = (prop.findtext("german") or "").strip()
        ogden = (prop.findtext("ogden") or "").strip()
        pmc = (prop.findtext("pears_mcguinness") or "").strip()

        proposition = Proposition(
            name=name,
            text=german or ogden or pmc,  # fallback if German empty
            level=level,
            sort_order=idx,
        )
        session.add(proposition)
        lookup[name] = proposition

    session.flush()

    # --- 2. establish hierarchy ---
    for name, proposition in lookup.items():
        if "." not in name:
            continue
        parent_name = name.rsplit(".", 1)[0]
        parent = lookup.get(parent_name)
        if parent is not None:
            proposition.parent = parent

    session.flush()

    # --- 3. create translations for each proposition ---
    for prop in rows:
        name = prop.get("id")
        if not name or name not in lookup:
            continue
        german = (prop.findtext("german") or "").strip()
        ogden = (prop.findtext("ogden") or "").strip()
        pmc = (prop.findtext("pears_mcguinness") or "").strip()
        base = lookup[name]

        translations = [
            ("de", german, "German original"),
            ("en-ogden", ogden, "Ogden/Ramsey 1922"),
            ("en-pmc", pmc, "Pears/McGuinness 1961"),
        ]
        for lang, text, src in translations:
            if not text:
                continue
            tr = Translation(lang=lang, text=text, source=src, proposition=base)
            session.add(tr)

    session.commit()
    session.close()
    return len(lookup)
