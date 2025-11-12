# Tractatus




# **Tractatus ORM Project – Concept and Architecture Overview**

## **1. Purpose**

This project builds a **persistent, navigable digital structure** for hierarchical philosophical or scriptural texts — beginning with *Ludwig Wittgenstein’s Tractatus Logico-Philosophicus*.
Its purpose is to model such works not as flat text files, but as **semantic trees** of propositions that can be queried, linked, translated, and analyzed programmatically.

The same design can be used later for other structured corpora — such as the **Bible**, **Qur’an**, **Upanishads**, or multi-layered commentaries — where every verse or statement is part of a larger hierarchy.

---

## **2. Core Idea**

Each proposition in the *Tractatus* has a **hierarchical address** —
for example:

```
1
1.1
1.11
1.12
```

Each deeper level expands the parent.
The project formalizes this pattern as a **recursive data structure**:
every proposition knows its **parent**, **children**, **depth**, and **order**.

Once ingested, the text becomes a **symbolic skeleton** that supports:

* Recursive traversal (e.g. fetch all descendants of “2”),
* Multilingual translation mapping,
* Commentary, cross-reference, or semantic annotation layers.

This is both a **research database** and a **conceptual model of meaning** — a minimal ontology for structured language.

---

## **3. Technical Approach**

The project uses **SQLAlchemy ORM** (Object-Relational Mapper) to combine:

* the **reliability of a relational database** (SQLite by default), and
* the **natural navigation of Python objects** (`.parent`, `.children`, `.translations`).

Thus, the database schema and the in-memory object graph are isomorphic:

```python
root = Proposition(name="1", text="The world is everything that is the case.")
child = Proposition(name="1.1", text="The world is the totality of facts.", parent=root)
```

SQLAlchemy handles persistence, relationships, and recursive queries transparently.

---

## **4. Project Architecture**

```
tractatus_orm/
├── database.py        # database engine, session factory, initialization
├── models.py          # ORM classes (Proposition, Translation)
├── ingest.py          # ingestion of numbered text into the hierarchy
├── main.py            # simple exploration / printing of hierarchy
├── tractatus.txt      # source text file (numbered lines)
└── tractatus.db       # generated SQLite database
```

### **Tables**

| Table                   | Description                                                                  |
| ----------------------- | ---------------------------------------------------------------------------- |
| `tractatus`             | Stores propositions: id, name (`1.1.2`), text, parent_id, level, sort_order. |
| `tractatus_translation` | Stores multilingual versions linked to `tractatus.id`.                       |

### **Relationships**

* `Proposition.parent` ↔ `Proposition.children` (recursive self-reference)
* `Proposition.translations` ↔ `Translation.proposition`

---

## **5. Ingestion Workflow**

The ingestion process runs in two phases:

1. **Flat ingestion:**
   Parse each numbered line (`1.1.2 …`) and insert a record with name, text, and level.

2. **Hierarchy resolution:**
   After all records exist, resolve parent-child relationships numerically
   (`1.1.2` → parent `1.1` → parent `1`).

Each record receives a stable **numeric ID** that serves as an anchor for:

* translations,
* commentaries,
* future cross-textual linking.

---

## **6. Usage**

### Build and Explore

```bash
python ingest.py        # builds the tractatus.db hierarchy from tractatus-raw.txt
python main.py          # prints the structure from root down
```

The ingestion process currently uses the German text embedded in
`tractatus-raw.txt`. The raw source contains the complete bilingual edition,
but only the German portion preserves consistent proposition numbering. The
`tractatus_orm.text_cleaner` module exposes helpers for extracting these entries
from the raw file.

### Interactive Exploration

```python
from database import SessionLocal
from models import Proposition

session = SessionLocal()
root = session.query(Proposition).filter_by(name="1").first()
for child in root.children:
    print(child.name, child.text)
```

### Command-line Interface and LLM helpers

The project ships with an interactive CLI that wraps the ORM session and
provides helper commands for navigating the hierarchy or handing content to
an LLM-backed assistant.

```bash
python trcli.py
```

Key commands once the prompt `(tractatus)` is displayed:

| Command | Description |
| ------- | ----------- |
| `get <name>` | Jump directly to a proposition by its dotted identifier (`get 1.2.3`). Use `get id:<n>` to target the numeric database identifier. |
| `list [name]` | Show the immediate children of the current proposition or of the supplied target (`list 2`). |
| `tree` | Print the full subtree for the current proposition. |
| `ag` / `agent` | Send the current or selected propositions to the LLM router. Examples: `ag comment` (comment on the current node), `ag 2 list comparison` (summarise the children of proposition `2` and compare them). |

You can also combine navigation and LLM calls inline with prefixes such as
`1.1 ag:comment` to jump to `1.1` and immediately request an LLM comment.
If no OpenAI credentials are configured the CLI falls back to an echo agent,
so the command structure can be explored without an external dependency.

### Web Interface

For a more visual, browser-based experience, use the **Flask web wrapper**:

```bash
pip install flask flask-cors
python web_app.py
# Visit http://localhost:5000
```

The web interface provides:

* **Interactive UI** with tabbed browsing (Children, Tree, Search, AI Analysis, Settings)
* **REST API** for all operations (use `curl` or any HTTP client)
* **Command history** for quick re-execution
* **Real-time configuration** panel
* **Beautiful, responsive design** optimized for both desktop and mobile

See [WEB_INTERFACE.md](WEB_INTERFACE.md) for complete documentation on the REST API, endpoints, and usage examples.

The web and CLI share the same **service layer** (`TractatusService`), ensuring consistency across both interfaces.

---

## **7. Design Philosophy**

The system treats texts as **living object graphs** rather than static strings.

* Each node is a **symbolic unit** with position and meaning.
* Relationships express **logical dependency**, not just sequence.
* Language versions and commentaries are **layers**, not replacements.

This reflects the *Tractatus* itself: a structure of propositions that recursively define and depend on one another.

---

## **8. Extensibility**

Future modules will extend this same skeleton to:

* Ingest **translations** (`ingest_translation.py`)
* Support **commentary layers**
* Export to **RDF / Neo4j** for semantic graph analysis
* Add **full-text search** (SQLite FTS / Postgres)
* Provide a **FastAPI interface** for REST access

The design is **data-agnostic** — any hierarchical corpus can be imported by providing a correctly numbered text file.

---

## **9. Current Status**

Implemented:
none yet

🚧 Next steps:


* Database schema and ORM model
* Two-phase ingestion (hierarchy + numeric linking)
* Simple CLI and exploration script

* Translation ingestion via ORM
* Optional REST API or graph export layer

---

## **10. Summary**

**Tractatus ORM** builds a symbolic database that makes hierarchical thought structures machine-navigable.
It begins with Wittgenstein but generalizes into a universal framework for recursive texts, allowing translation, commentary, and computational interpretation.

