"""JSON-based persistent storage for expenses."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .expense import Expense, ValidationError


class StorageError(Exception):
    """Raised when storage operations fail."""


class ExpenseStore:
    """Persists expenses to a JSON file."""

    def __init__(self, path: str | os.PathLike[str] = "expenses.json") -> None:
        self.path = Path(path)

    def load(self) -> list[Expense]:
        """Load all expenses from disk. Returns [] if file is missing."""
        if not self.path.exists():
            return []
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Cannot read {self.path}: {exc}") from exc
        if not raw.strip():
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageError(f"Corrupt data file {self.path}: {exc}") from exc
        entries = data.get("expenses") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise StorageError(f"Corrupt data file {self.path}: expected a list.")

        expenses: list[Expense] = []
        for index, item in enumerate(entries):
            if not isinstance(item, dict):
                raise StorageError(
                    f"Corrupt data file {self.path}: entry {index} is not an object."
                )
            try:
                expenses.append(Expense.from_dict(item))
            except ValidationError as exc:
                raise StorageError(
                    f"Corrupt data file {self.path}: entry {index}: {exc}"
                ) from exc
        return expenses

    def save(self, expenses: list[Expense]) -> None:
        """Atomically persist expenses to disk."""
        payload = {
            "version": 1,
            "expenses": [e.to_dict() for e in expenses],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
        except OSError as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise StorageError(f"Cannot write {self.path}: {exc}") from exc

    def exists(self) -> bool:
        return self.path.exists()
