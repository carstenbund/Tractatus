"""SQLAlchemy ORM models for Tractatus Logico-Philosophicus.

This module defines the data models for storing and navigating the hierarchical
structure of Wittgenstein's Tractatus. The core design uses a recursive tree
structure to represent the numbered propositions and their relationships.

Data Model:
    Proposition: A single numbered proposition (e.g., "1", "1.1", "1.11")
        - Stores German original text
        - Self-referential parent-child relationships create tree structure
        - Example hierarchy: 1 -> 1.1 -> 1.11, 1.12

    Translation: Multilingual translations and alternative text versions
        - Multiple translations per proposition (en, fr, pt, etc.)
        - Alternative versions with metadata (editor, tags, timestamps)
        - Supports both official translations and user-contributed alternatives
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Proposition(Base):
    """A single proposition in the Tractatus hierarchical structure.

    Each proposition represents a numbered statement in Wittgenstein's work,
    with a hierarchical numbering system (1, 1.1, 1.11, etc.). Propositions
    form a tree structure through parent-child relationships.

    Attributes:
        id: Database primary key (auto-incrementing integer)
        name: Hierarchical address (e.g., "1", "1.1", "2.0121") - unique identifier
        text: The proposition text in German (original language)
        level: Depth in hierarchy (1 for "1", 2 for "1.1", 3 for "1.11", etc.)
        sort_order: Integer for sorting siblings in correct hierarchical order
        parent_id: Foreign key to parent proposition (None for root propositions like "1", "2")

    Relationships:
        parent: Single parent proposition (recursive self-reference)
        children: List of child propositions (recursive, ordered by sort_order)
        translations: List of translations and alternative versions

    Examples:
        Proposition(name="1", text="Die Welt ist alles, was der Fall ist.", level=1)
        -> Root proposition with children 1.1, 1.2, etc.

        Proposition(name="1.1", text="...", level=2, parent_id=<id of "1">)
        -> Child of proposition "1"
    """
    __tablename__ = "tractatus"

    # Primary key and hierarchical identifier
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Hierarchy metadata
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Self-referential foreign key for tree structure
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tractatus.id"), nullable=True)

    # Recursive parent relationship (many-to-one)
    parent: Mapped["Proposition"] = relationship(
        "Proposition",
        remote_side="Proposition.id",  # Specifies the "one" side of the relationship
        back_populates="children",
    )

    # Recursive children relationship (one-to-many)
    children: Mapped[list["Proposition"]] = relationship(
        "Proposition",
        back_populates="parent",
        cascade="all, delete-orphan",  # Delete children when parent is deleted
        order_by="Proposition.sort_order",  # Automatically sort by hierarchical order
    )

    # Translations and alternative versions
    translations: Mapped[list["Translation"]] = relationship(
        "Translation",
        back_populates="proposition",
        cascade="all, delete-orphan",  # Delete translations when proposition is deleted
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Developer-friendly representation showing name and text preview."""
        return f"<Proposition {self.name}: {self.text[:40]!r}>"

    def path(self) -> str:
        """Compute full hierarchical path from root to this proposition.

        Walks up the parent chain to build the complete path. Note that this
        may differ from the name for deeply nested propositions.

        Returns:
            Dot-separated path string (e.g., "1.1.2")

        Example:
            Proposition "1.1" -> "1.1"
            Proposition "2.0121" -> "2.01.2.1" (if parent chain differs)
        """
        node: Proposition | None = self
        lineage: list[str] = []
        while node is not None:
            lineage.insert(0, node.name)
            node = node.parent
        return ".".join(lineage)

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        """User-friendly string representation for display."""
        return f"{self.name}: {self.text}"


class Translation(Base):
    """Multilingual translation or alternative version of a proposition.

    This model stores both official translations (e.g., English, French, Portuguese)
    and user-contributed alternative text versions. Each translation is linked to
    a specific proposition and can have metadata like editor, tags, and timestamps.

    The model supports two use cases:
    1. Official translations: variant_type="translation", source="Pears & McGuinness"
    2. Alternative versions: variant_type="alternative", source="user", with metadata

    Attributes:
        id: Database primary key (auto-incrementing integer)
        lang: Language code (e.g., "en", "fr", "pt", "de")
        text: Translated or alternative text content
        source: Source of translation (e.g., "Pears & McGuinness", "user", "OpenAI")
        tractatus_id: Foreign key to the associated Proposition
        variant_type: Type of translation ("translation" or "alternative")
        editor: Name of editor/contributor (for alternative versions)
        tags: Comma-separated tags for categorization (e.g., "modern,simplified")
        created_at: Timestamp when translation was created
        updated_at: Timestamp when translation was last modified

    Relationships:
        proposition: The associated Proposition object

    Examples:
        # Official English translation
        Translation(
            lang="en",
            text="The world is everything that is the case.",
            source="Pears & McGuinness",
            variant_type="translation"
        )

        # User-contributed alternative
        Translation(
            lang="en",
            text="The world consists of all that actually occurs.",
            source="user",
            variant_type="alternative",
            editor="John Doe",
            tags="modern,simplified"
        )
    """
    __tablename__ = "tractatus_translation"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Language and content
    lang: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    # Foreign key to proposition
    tractatus_id: Mapped[int | None] = mapped_column(ForeignKey("tractatus.id"))

    # Variant type: "translation" (official) or "alternative" (user-contributed)
    variant_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="translation", server_default="translation"
    )

    # Additional metadata for alternative versions
    editor: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # Comma-separated

    # Timestamps for tracking creation and updates
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),  # Python-side default
        server_default=func.now(),  # Database-side default
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),  # Automatically update on modification
    )

    # Relationship back to the proposition
    proposition: Mapped[Proposition] = relationship("Proposition", back_populates="translations")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        """Developer-friendly representation showing language and text preview."""
        return f"<Translation {self.lang}: {self.text[:40]!r}>"
