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
pip install -r requirements.txt
python web_app.py
# Visit http://localhost:5000
```

**Features:**

* **Interactive tabbed UI:**
  - **Children** — Browse immediate children of current proposition
  - **Tree** — Visualize full subtree hierarchy
  - **Search** — Full-text search across propositions
  - **AI Analysis** — Generate comments, comparisons, web searches, references
  - **Settings** — Configure preferences in real-time

* **REST API** for all operations (use `curl` or any HTTP client):
  - `POST /api/get` — Fetch a proposition
  - `POST /api/list` — List children
  - `POST /api/children` — Get immediate children of current
  - `POST /api/parent` — Navigate to parent
  - `POST /api/next` — Navigate to next sibling
  - `POST /api/previous` — Navigate to previous sibling
  - `POST /api/search` — Full-text search
  - `POST /api/agent` — Invoke LLM analysis
  - `GET /api/config` — Get all settings
  - `POST /api/config/set` — Update setting

* **Command history** with clickable recall — Re-execute previous commands instantly

* **Language selector** — Switch between German original and English translation, affecting both UI text and LLM response language

* **Real-time configuration** — Update preferences like `llm_max_tokens` and `display_length` without restarting

* **Beautiful, responsive design** — Optimized for mobile, tablet, and desktop with:
  - 44px minimum touch targets on all buttons
  - Mobile-first three-breakpoint layout system
  - Smooth transitions and interactive feedback
  - Gradient background with modern aesthetics

**Example API Call:**

```bash
curl -X POST http://localhost:5000/api/get \
  -H "Content-Type: application/json" \
  -d '{"key": "1.1"}'
```

See [WEB_INTERFACE.md](WEB_INTERFACE.md) for complete REST API documentation with examples.

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

### **Implemented Features** ✅

**Core Infrastructure:**
* ✅ Database schema and ORM model (SQLAlchemy)
* ✅ Two-phase ingestion with hierarchy resolution
* ✅ Multilingual support (German original + English translation)

**Command-Line Interface (CLI):**
* ✅ Interactive command prompt with command history
* ✅ Navigation commands: `get`, `list`, `children`, `parent`, `next`, `previous`
* ✅ Proposition search with `search <term>`
* ✅ Translation lookup with `translations` and `translate <lang>`
* ✅ LLM agent integration: `ag comment`, `ag comparison`, `ag websearch`, `ag reference`
* ✅ Preference management: `set <key> <value>` with persistent `.trclirc` config
* ✅ Configuration commands: `config`, `config reset`
* ✅ Configurable settings:
  - `display_length` - Output width for truncation
  - `lines_per_output` - Number of results per display
  - `llm_max_tokens` - Control LLM response length (10-4000 tokens)
  - `lang` - Language preference (en/de)

**Web Interface:**
* ✅ Flask REST API with JSON responses
* ✅ Single-page application (SPA) with tabbed UI
* ✅ Interactive browser-based navigation
* ✅ Command execution from web interface
* ✅ Real-time command history with clickable recall
* ✅ Language selector affecting both text display and LLM responses
* ✅ Settings panel for runtime configuration
* ✅ Beautiful responsive design optimized for mobile, tablet, and desktop

**LLM Integration:**
* ✅ OpenAI integration with configurable response length
* ✅ System prompt + user prompt architecture for better context
* ✅ Action-specific prompting (comment, comparison, websearch, reference)
* ✅ Language-aware response generation
* ✅ Echo fallback mode for testing without API keys

**Responsive Design:**
* ✅ Mobile-first CSS with three breakpoints
  - Mobile (≤480px): Optimized layout, 44px touch buttons, hidden history
  - Tablet (481-768px): Balanced spacing, 2-column grids
  - Desktop (769px+): Full features, hover effects, multi-column layouts
* ✅ Touch-friendly button sizing (44px minimum)
* ✅ Responsive typography and spacing

**Deployment & Configuration:**
* ✅ Koyeb deployment configuration
* ✅ Docker containerization (Dockerfile, docker-compose.yml)
* ✅ Environment-based configuration (DATABASE_URL, PORT, OPENAI_API_KEY)
* ✅ Production setup with gunicorn
* ✅ Comprehensive deployment documentation

**Bug Fixes:**
* ✅ Fixed command history functionality (variable naming conflict resolution)

### **Bug Fixes & Recent Updates**

**Latest Fix (Current Branch):**
Fixed critical bug in command history where the `commandHistory` array was being overwritten with a DOM element reference. This prevented history tracking from working. The fix:
- Renamed DOM element variable to `commandHistoryEl`
- Preserved `commandHistory` array for command storage
- History now properly tracks and displays executed commands
- Clicking history items restores commands to input field

🚧 **Next Steps:**

* Export to RDF / Neo4j for semantic graph analysis
* Full-text search implementation (SQLite FTS or PostgreSQL)
* Comment layers and scholarly annotations
* Support for additional hierarchical texts (Bible, Qur'an, etc.)
* Advanced analytics and proposition relationship visualization

---

## **10. Summary**

**Tractatus ORM** builds a symbolic database that makes hierarchical thought structures machine-navigable.
It begins with Wittgenstein but generalizes into a universal framework for recursive texts, allowing translation, commentary, and computational interpretation.

---

Would you like me to format this as a `README.md` (with Markdown headings, code fences, etc.) for direct inclusion in your repository?
