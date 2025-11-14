"""Populate translations for Tractatus propositions using OpenAI Chat Completions."""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable

from openai import OpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tractatus_orm.database import SessionLocal
from tractatus_orm.models import Proposition, Translation


DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_LANG = "en-gpt"


class TranslationJob:
    """Handle iterating through propositions and persisting translations."""

    def __init__(
        self,
        *,
        session: Session,
        client: OpenAI,
        lang: str,
        model: str,
        start_id: int | None = None,
        end_id: int | None = None,
        sleep: float = 0.0,
        dry_run: bool = False,
        overwrite: bool = False,
    ) -> None:
        self.session = session
        self.client = client
        self.lang = lang
        self.model = model
        self.sleep = sleep
        self.dry_run = dry_run
        self.overwrite = overwrite

        max_id = session.scalar(select(func.max(Proposition.id)))
        if max_id is None:
            raise RuntimeError("No propositions found in the database.")

        self.start_id = start_id if start_id is not None else 1
        self.end_id = end_id if end_id is not None else max_id
        if self.start_id < 1:
            raise ValueError("start_id must be >= 1")
        if self.end_id < self.start_id:
            raise ValueError("end_id must be greater than or equal to start_id")
        if self.end_id > max_id:
            self.end_id = max_id

    def _existing_translation(self, proposition_id: int) -> Translation | None:
        stmt = select(Translation).where(
            Translation.tractatus_id == proposition_id,
            Translation.lang == self.lang,
        )
        return self.session.scalars(stmt).first()

    def _translate(self, proposition: Proposition) -> str:
        system_message = (
            "You are a careful literary translator working on Ludwig Wittgenstein's "
            "Tractatus Logico-Philosophicus."
        )
        user_message = (
            "Provide a natural translation of the following proposition into the "
            f"target language '{self.lang}'.\n"
            "Return only the translated text without commentary.\n"
            f"Proposition {proposition.name}: {proposition.text}"
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            max_tokens=600,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

    def _store_translation(self, proposition: Proposition, text: str, existing: Translation | None) -> None:
        source = f"OpenAI {self.model}"
        if self.dry_run:
            print(f"[dry-run] Would store translation for {proposition.name}: {text[:60]}")
            return

        if existing and self.overwrite:
            existing.text = text
            existing.source = source
            print(f"Updated translation for {proposition.name} ({self.lang}).")
        elif existing:
            print(f"Skipping {proposition.name}; translation already exists.")
            return
        else:
            translation = Translation(
                lang=self.lang,
                text=text,
                source=source,
                proposition=proposition,
            )
            self.session.add(translation)
            print(f"Inserted translation for {proposition.name} ({self.lang}).")

        self.session.commit()

    def run(self) -> None:
        for proposition in self._iter_propositions():
            existing = self._existing_translation(proposition.id)
            if existing and not self.overwrite:
                print(f"Skipping {proposition.name}; translation already exists.")
                continue

            try:
                translated = self._translate(proposition)
            except Exception as exc:  # pragma: no cover - runtime guard for API issues
                print(f"Error translating {proposition.name}: {exc}", file=sys.stderr)
                break

            if not translated:
                print(
                    f"Warning: empty translation received for {proposition.name}.",
                    file=sys.stderr,
                )
                continue

            self._store_translation(proposition, translated, existing)

            if self.sleep:
                time.sleep(self.sleep)

    def _iter_propositions(self) -> Iterable[Proposition]:
        for pid in range(self.start_id, self.end_id + 1):
            proposition = self.session.get(Proposition, pid)
            if proposition is None:
                continue
            yield proposition


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", default=DEFAULT_LANG, help="Target language code to store in the database.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI chat completion model name.")
    parser.add_argument("--start-id", type=int, help="Optional starting proposition id (inclusive).")
    parser.add_argument("--end-id", type=int, help="Optional ending proposition id (inclusive).")
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Optional pause in seconds between API calls to respect rate limits.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying the database.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing translations for the chosen language.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    client = OpenAI()

    with SessionLocal() as session:
        job = TranslationJob(
            session=session,
            client=client,
            lang=args.lang,
            model=args.model,
            start_id=args.start_id,
            end_id=args.end_id,
            sleep=args.sleep,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
        job.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
