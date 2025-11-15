from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Proposition(Base):
    __tablename__ = "tractatus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tractatus.id"), nullable=True)

    parent: Mapped["Proposition"] = relationship(
        "Proposition",
        remote_side="Proposition.id",
        back_populates="children",
    )
    children: Mapped[list["Proposition"]] = relationship(
        "Proposition",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Proposition.sort_order",
    )
    translations: Mapped[list["Translation"]] = relationship(
        "Translation",
        back_populates="proposition",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Proposition {self.name}: {self.text[:40]!r}>"

    def path(self) -> str:
        node: Proposition | None = self
        lineage: list[str] = []
        while node is not None:
            lineage.insert(0, node.name)
            node = node.parent
        return ".".join(lineage)

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        return f"{self.name}: {self.text}"


class Translation(Base):
    __tablename__ = "tractatus_translation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lang: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    tractatus_id: Mapped[int | None] = mapped_column(ForeignKey("tractatus.id"))
    variant_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="translation", server_default="translation"
    )
    editor: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    proposition: Mapped[Proposition] = relationship("Proposition", back_populates="translations")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Translation {self.lang}: {self.text[:40]!r}>"
