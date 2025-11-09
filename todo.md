

## **1. Project Layout**

Structure the files like this:

```
tractatus_orm/
├── models.py          # ORM models and relationships
├── database.py        # engine, session, initialization
├── ingest.py          # ingestion logic for Tractatus text
├── main.py            # entry point (for testing / exploration)
├── tractatus.txt      # source text
└── tractatus.db       # generated SQLite database
```

---

## **2. database.py**

This file initializes the SQLAlchemy engine and session.

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///tractatus.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def init_db():
    from models import Proposition, Translation  # avoid circular import
    Base.metadata.create_all(bind=engine)
```

---

## **3. models.py**

Define your core ORM entities: propositions and translations.

```python
# models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Proposition(Base):
    __tablename__ = "tractatus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    text = Column(Text, nullable=False)
    level = Column(Integer)
    sort_order = Column(Integer)
    parent_id = Column(Integer, ForeignKey("tractatus.id"), nullable=True)

    parent = relationship("Proposition", remote_side=[id], back_populates="children")
    children = relationship("Proposition", back_populates="parent", cascade="all, delete-orphan")
    translations = relationship("Translation", back_populates="proposition", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proposition {self.name}: {self.text[:40]!r}>"

    def path(self):
        node, lineage = self, []
        while node:
            lineage.insert(0, node.name)
            node = node.parent
        return '.'.join(lineage)

    def __str__(self):
        return f"{self.name}: {self.text}"

class Translation(Base):
    __tablename__ = "tractatus_translation"

    id = Column(Integer, primary_key=True)
    lang = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    source = Column(String)
    tractatus_id = Column(Integer, ForeignKey("tractatus.id"))

    proposition = relationship("Proposition", back_populates="translations")

    def __repr__(self):
        return f"<Translation {self.lang}: {self.text[:40]!r}>"
```

---

## **4. ingest.py**

Handles text ingestion (two-phase as before, but ORM-aware).

```python
# ingest.py
import re
from models import Proposition
from database import SessionLocal, init_db

def ingest_text(file_path: str):
    init_db()
    session = SessionLocal()
    lookup = {}

    # --- Phase 1: insert all propositions ---
    with open(file_path, encoding="utf-8") as f:
        for idx, line in enumerate(f):
            m = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)", line.strip())
            if not m:
                continue
            name, text = m.group(1), m.group(2)
            level = name.count('.') + 1
            prop = Proposition(name=name, text=text, level=level, sort_order=idx)
            lookup[name] = prop
            session.add(prop)

    session.flush()  # ensures all IDs exist before linking

    # --- Phase 2: resolve parent-child relations ---
    for name, prop in lookup.items():
        if '.' not in name:
            continue
        parent_name = '.'.join(name.split('.')[:-1])
        prop.parent = lookup.get(parent_name)

    session.commit()
    session.close()
    print(f"Ingested {len(lookup)} propositions.")

if __name__ == "__main__":
    ingest_text("tractatus.txt")
```

---

## **5. main.py**

A small exploration shell — so you can play with the data once it’s ingested.

```python
# main.py
from database import SessionLocal, init_db
from models import Proposition

def explore():
    init_db()
    session = SessionLocal()

    root = session.query(Proposition).filter_by(name="1").first()

    def print_tree(node, depth=0):
        print("  " * depth + f"{node.name}: {node.text}")
        for child in sorted(node.children, key=lambda c: c.sort_order):
            print_tree(child, depth + 1)

    print_tree(root)
    session.close()

if __name__ == "__main__":
    explore()
```

---

## **6. Running the System**

1. Prepare your text file `tractatus.txt` — one proposition per line, e.g.:

   ```
   1 The world is everything that is the case.
   1.1 The world is the totality of facts, not of things.
   1.11 A fact is the existence of states of affairs.
   ```

2. Ingest it:

   ```bash
   python ingest.py
   ```

   → Creates `tractatus.db` with hierarchy resolved.

3. Explore:

   ```bash
   python main.py
   ```

---

## **7. Example ORM Queries**

In an interactive shell (e.g. `ipython`):

```python
from database import SessionLocal
from models import Proposition

session = SessionLocal()

# Get a specific proposition
p = session.query(Proposition).filter_by(name="1.1").first()
print(p.text)

# See parent
print("Parent:", p.parent.name, p.parent.text)

# See children
for c in p.children:
    print("Child:", c.name, c.text)

# Add a translation
p.translations.append(Translation(lang="de", text="Die Welt ist die Gesamtheit der Tatsachen."))
session.commit()
```

---

## **8. Benefits of the ORM Model**

| Layer                         | Benefit                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| **SQL backend**               | Reliable, indexed, ACID-compliant.                                                    |
| **Object graph**              | Direct `.children` and `.parent` navigation.                                          |
| **Translation extensibility** | Easy to attach multilingual data via relationship.                                    |
| **ORM-level querying**        | Recursive traversal, joins, filters, etc.                                             |
| **Future scalability**        | You can switch to PostgreSQL or add Alembic migrations later without rewriting logic. |

---

### **Optional next step**

We can now easily add a **translation ingestion** module:

```bash
python ingest_translation.py --file tractatus_de.txt --lang de --source "Wiener Ausgabe"
```

that uses the same ORM relationships to link translated text to each proposition by `name`.

Would you like me to add that next — a translation ingestion script compatible with this ORM setup?
