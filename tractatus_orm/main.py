from __future__ import annotations

from collections.abc import Iterable

from .database import SessionLocal, init_db
from .models import Proposition


def walk(node: Proposition) -> Iterable[Proposition]:
    yield node
    for child in node.children:
        yield from walk(child)


def print_tree(node: Proposition, depth: int = 0) -> None:
    indent = "  " * depth
    print(f"{indent}{node.name}: {node.text}")
    for child in node.children:
        print_tree(child, depth + 1)


def explore(root_name: str = "1") -> None:
    init_db()
    session = SessionLocal()
    try:
        root = session.query(Proposition).filter_by(name=root_name).first()
        if root is None:
            raise ValueError(f"Proposition '{root_name}' not found.")
        print_tree(root)
    finally:
        session.close()


if __name__ == "__main__":
    explore()
