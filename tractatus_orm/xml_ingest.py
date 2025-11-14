from html import unescape
from pathlib import Path
import xml.etree.ElementTree as ET

from .database import SessionLocal, init_db
from .models import Proposition, Translation


# Mapping from XML tag name to (language code, default source description).
# The default source can be overridden by a "source" attribute on the XML
# element itself, which enables new material (such as the continuation text)
# to annotate its provenance without requiring code changes.
TRANSLATION_TAGS = {
    "german": ("de", "German original"),
    "ogden": ("en-ogden", "Ogden/Ramsey 1922"),
    "pears_mcguinness": ("en-pmc", "Pears/McGuinness 1961"),
    "english": ("en", "English translation"),
}


# Subset of HTML entities that commonly appear in the XML source files. The
# default XML parser in the standard library only recognises the XML predefined
# entities (such as &amp; and &quot;), so we register the additional ones we rely on
# here to avoid parse errors.
HTML_ENTITY_MAP = {
    "mdash": "—",
    "ndash": "–",
}


def _find_parent_by_longest_prefix(name: str, lookup: dict[str, Proposition]) -> str | None:
    """
    Find parent using longest matching prefix algorithm.

    This properly handles Wittgenstein's hierarchical numbering where:
    - 2.01 is parent of 2.011, 2.012 (not just sibling)
    - 2.012 is parent of 2.0121 (not just sibling)

    Algorithm: Find the longest string that is a proper prefix of 'name'
    and exists in the lookup table.

    For a name like '2.0121':
    1. Try all prefixes by removing characters from the end
    2. '2.012' (remove '1') → exists? YES → return
    3. If not found, '2.01' (remove '21') → exists? check
    4. Then '2.0' → check
    5. Finally '2' → check (must exist if name has '.' prefix)

    Examples:
    - Parent of '2.0121' is '2.012' (longest prefix that exists)
    - Parent of '2.012' is '2.01' (longest prefix that exists)
    - Parent of '2.01' is '2' (longest prefix that exists)
    - Parent of '2' is None (no prefix)
    """
    if "." not in name:
        return None

    # Try progressively shorter prefixes by removing characters from the end
    # For "2.0121", try: "2.012", "2.01", "2.0", "2"
    for length in range(len(name) - 1, 0, -1):
        candidate = name[:length]
        if candidate in lookup:
            return candidate

    return None


def _calculate_level(name: str, lookup: dict[str, Proposition], parent_map: dict[str, str | None]) -> int:
    """
    Calculate hierarchical level by traversing parent chain.

    Level = distance from root + 1
    Examples:
    - '1' → level 1
    - '1.1' → level 2 (parent: 1)
    - '1.11' → level 3 (parent: 1.1 → parent: 1)
    - '1.111' → level 4 (parent: 1.11 → parent: 1.1 → parent: 1)
    """
    level = 1
    current = name

    while parent_map.get(current) is not None:
        current = parent_map[current]
        level += 1

    return level


def _iter_translation_nodes(prop: ET.Element) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for node in prop:
        tag = node.tag.strip().lower()
        if tag not in TRANSLATION_TAGS:
            continue
        text = (node.text or "").strip()
        if not text:
            continue
        lang, default_source = TRANSLATION_TAGS[tag]
        source = node.attrib.get("source", default_source)
        entries.append((lang, text, source))
    return entries


def ingest_multilang_xml(file_path: str | Path) -> int:
    init_db()
    session = SessionLocal()
    lookup: dict[str, Proposition] = {}

    parser = ET.XMLParser()
    for name, value in HTML_ENTITY_MAP.items():
        parser.entity[name] = value
    xml_text = Path(file_path).read_text(encoding="utf-8")
    xml_text = unescape(xml_text)
    root = ET.fromstring(xml_text, parser=parser)
    rows = root.findall(".//proposition")

    # --- Phase 1: Create propositions (with German text as base, placeholder levels) ---
    for idx, prop in enumerate(rows):
        name = prop.get("id")
        if not name:
            continue

        translations = _iter_translation_nodes(prop)
        base_text = ""
        for lang, text, _source in translations:
            if lang == "de":
                base_text = text
                break
        if not base_text and translations:
            # Fall back to the first available translation if German text is absent.
            base_text = translations[0][1]

        proposition = Proposition(
            name=name,
            text=base_text,
            level=1,  # Placeholder, will be updated
            sort_order=idx,
        )
        session.add(proposition)
        lookup[name] = proposition

    session.flush()

    # --- Phase 2: Establish hierarchy using longest prefix matching ---
    parent_map: dict[str, str | None] = {}

    for name, proposition in lookup.items():
        parent_name = _find_parent_by_longest_prefix(name, lookup)
        parent_map[name] = parent_name

        if parent_name is not None:
            parent = lookup[parent_name]
            proposition.parent = parent

    # --- Phase 3: Recalculate levels based on actual parent chain ---
    for name, proposition in lookup.items():
        proposition.level = _calculate_level(name, lookup, parent_map)

    session.flush()

    # --- Phase 4: Create translations for each proposition ---
    for prop in rows:
        name = prop.get("id")
        if not name or name not in lookup:
            continue
        base = lookup[name]
        for lang, text, src in _iter_translation_nodes(prop):
            tr = Translation(lang=lang, text=text, source=src, proposition=base)
            session.add(tr)

    session.commit()
    session.close()
    return len(lookup)


def main() -> None:
    xml_path = Path(__file__).resolve().parents[1] / "tractatus.xml"
    if not xml_path.exists():
        print(f"Error: XML file not found at {xml_path}")
        print("Please ensure tractatus.xml exists in the project root directory.")
        return
    count = ingest_multilang_xml(xml_path)
    print(f"Ingested {count} propositions with translations from {xml_path.name}.")


if __name__ == "__main__":
    main()
