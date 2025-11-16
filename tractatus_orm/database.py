"""Database configuration and initialization for Tractatus ORM.

This module sets up SQLAlchemy database connectivity and handles schema
initialization and migrations. It uses SQLite for simplicity but can be
configured to use PostgreSQL in production environments.

Key Components:
    - Database engine configuration
    - Session factory for ORM operations
    - Base class for declarative models
    - Schema initialization and migration logic

Migration Strategy:
    Instead of using a full migration framework like Alembic, this module
    uses a simple column-checking approach to add missing columns to legacy
    databases. This is appropriate for the small schema and development context.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Database connection URL
# SQLite for development/single-user deployments (file-based database)
# For production with PostgreSQL, use: "postgresql://user:pass@host:port/dbname"
DATABASE_URL = "sqlite:///tractatus.db"

# SQLAlchemy engine - manages database connections
# echo=False: Don't log SQL statements (set to True for debugging)
# future=True: Use SQLAlchemy 2.0 API style
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Session factory - creates database sessions for ORM operations
# autoflush=False: Don't automatically flush changes before queries
# autocommit=False: Require explicit commits for transactions
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base class for all ORM models - provides SQLAlchemy declarative mapping
Base = declarative_base()


def init_db() -> None:
    """Initialize the database by creating all tables and running migrations.

    This function is called at application startup to ensure the database
    schema is up-to-date. It performs two operations:
    1. Creates any missing tables based on the ORM models
    2. Adds missing columns to existing tables (simple migration)

    The function is idempotent - safe to call multiple times.

    Note:
        Models are imported inside the function to avoid circular import issues
        during module initialization. The noqa comment suppresses linter warnings
        about unused imports (they're needed for metadata registration).
    """
    # Import inside function to avoid circular dependencies during module import.
    # These imports register the models with Base.metadata
    from .models import Proposition, Translation  # noqa: F401

    # Create all tables that don't exist yet (idempotent)
    Base.metadata.create_all(bind=engine)

    # Run migrations to add any missing columns to existing tables
    _ensure_translation_extensions()


def _ensure_translation_extensions() -> None:
    """Add missing columns to the translation table for legacy databases.

    This function implements a simple migration strategy for databases created
    before the alternative text feature was added. It checks for the presence
    of each column and adds missing ones using ALTER TABLE statements.

    Columns added:
        - variant_type: Distinguishes "translation" from "alternative" versions
        - editor: Name of the person who created the alternative
        - tags: Comma-separated tags for categorization
        - created_at: Timestamp when the record was created
        - updated_at: Timestamp when the record was last modified

    The migration is idempotent and safe to run multiple times. If all columns
    exist, no database changes are made.

    Implementation Notes:
        - Uses SQLAlchemy inspector to check existing schema
        - Executes raw SQL via text() for ALTER TABLE operations
        - Backfills timestamp columns with CURRENT_TIMESTAMP for existing rows
        - All operations run in a single transaction for consistency
    """

    # Get database inspector to query schema metadata
    inspector = inspect(engine)

    # Get list of existing columns (handle case where table doesn't exist yet)
    try:
        columns = {col["name"] for col in inspector.get_columns("tractatus_translation")}
    except Exception:
        # Table doesn't exist yet - it will be created by create_all()
        return

    # Build list of ALTER TABLE statements for missing columns
    statements: list[str] = []

    # Variant type column - distinguishes translation vs alternative
    if "variant_type" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN variant_type VARCHAR(32) NOT NULL DEFAULT 'translation'"
        )

    # Editor column - tracks who created alternative versions
    if "editor" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN editor VARCHAR"
        )

    # Tags column - comma-separated tags for categorization
    if "tags" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN tags TEXT"
        )

    # Build list of UPDATE statements to backfill timestamp columns
    updates: list[str] = []

    # Created timestamp - when the record was first created
    if "created_at" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN created_at DATETIME"
        )
        # Backfill existing rows with current timestamp
        updates.append(
            "UPDATE tractatus_translation SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )

    # Updated timestamp - when the record was last modified
    if "updated_at" not in columns:
        statements.append(
            "ALTER TABLE tractatus_translation ADD COLUMN updated_at DATETIME"
        )
        # Backfill existing rows with current timestamp
        updates.append(
            "UPDATE tractatus_translation SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
        )

    # If no columns are missing, nothing to do
    if not statements:
        return

    # Execute all migrations in a single transaction for consistency
    with engine.begin() as conn:
        # Add missing columns
        for stmt in statements:
            conn.execute(text(stmt))
        # Backfill timestamp values for existing rows
        for stmt in updates:
            conn.execute(text(stmt))
