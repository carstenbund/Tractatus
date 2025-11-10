from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass
class TranslationEntry:
    lang: str
    text: str
    source: str

@dataclass
class PropositionEntry:
    name: str
    level: int
    translations: list[TranslationEntry]


def extract_xml_propositions(file_path: str | Path) -> list[PropositionEntry]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    entries: list[PropositionEntry] = []

    for prop in root.findall(".//proposition"):
        name = prop.get("id")
        level = int(prop.get("depth", "1"))

        translations: list[TranslationEntry] = []
        if german := (prop.findtext("german") or "").strip():
            translations.append(TranslationEntry("de", german, "German original"))
        if ogden := (prop.findtext("ogden") or "").strip():
            translations.append(TranslationEntry("en-ogden", ogden, "Ogden/Ramsey 1922"))
        if pmc := (prop.findtext("pears_mcguinness") or "").strip():
            translations.append(TranslationEntry("en-pmc", pmc, "Pears/McGuinness 1961"))

        entries.append(PropositionEntry(name, level, translations))

    return entries
