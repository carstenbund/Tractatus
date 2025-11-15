from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///tractatus.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db() -> None:
    # Import inside function to avoid circular dependencies during module import.
    from .models import Proposition, Translation  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_translation_extensions()


def _ensure_translation_extensions() -> None:
    """Ensure legacy databases contain the extended translation columns."""

    inspector = inspect(engine)
    try:
        columns = {col["name"] for col in inspector.get_columns("tractatus_translation")}
    except Exception:
        return

    statements: list[str] = []
    if "variant_type" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN variant_type VARCHAR(32) NOT NULL DEFAULT 'translation'"
        )
    if "editor" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN editor VARCHAR"
        )
    if "tags" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN tags TEXT"
        )
    updates: list[str] = []
    if "created_at" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN created_at DATETIME"
        )
        updates.append(
            "UPDATE tractatus_translation SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )
    if "updated_at" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN updated_at DATETIME"
        )
        updates.append(
            "UPDATE tractatus_translation SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
        )

    if not statements:
        return

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        for stmt in updates:
            conn.execute(text(stmt))
