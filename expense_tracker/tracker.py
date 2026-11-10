"""Core expense tracker business logic."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable

from .expense import Expense, ValidationError, normalize_category, parse_amount, parse_date
from .storage import ExpenseStore, StorageError


class ExpenseTracker:
    """Manages a collection of expenses with JSON persistence."""

    def __init__(self, store: ExpenseStore | None = None) -> None:
        self.store = store if store is not None else ExpenseStore()
        self._expenses: dict[str, Expense] = {}
        self.load()

    # -- persistence ----------------------------------------------------

    def load(self) -> None:
        """(Re)load expenses from the backing store."""
        self._expenses = {e.expense_id: e for e in self.store.load()}

    def _persist(self) -> None:
        self.store.save(list(self._expenses.values()))

    # -- CRUD -----------------------------------------------------------

    def add_expense(
        self,
        amount: object,
        category: str,
        description: str = "",
        expense_date: object = None,
    ) -> Expense:
        """Create and store a new expense. Returns the Expense."""
        expense = Expense(
            amount=parse_amount(amount),
            category=normalize_category(category),
            description=description,
            expense_date=parse_date(expense_date) if expense_date is not None else date.today(),
        )
        if expense.expense_id in self._expenses:
            raise ValidationError("Generated expense ID collision; retry.")
        self._expenses[expense.expense_id] = expense
        try:
            self._persist()
        except StorageError:
            del self._expenses[expense.expense_id]
            raise
        return expense

    def get_expense(self, expense_id: str) -> Expense | None:
        return self._expenses.get(expense_id)

    def list_expenses(self) -> list[Expense]:
        """All expenses sorted by date descending, then id."""
        return sorted(
            self._expenses.values(),
            key=lambda e: (e.expense_date, e.expense_id),
            reverse=True,
        )

    def update_expense(self, expense_id: str, **fields: object) -> Expense:
        """Update fields of an existing expense. Unknown IDs raise KeyError."""
        expense = self._expenses.get(expense_id)
        if expense is None:
            raise KeyError(f"No expense with ID {expense_id!r}.")

        data = expense.to_dict()
        for key, value in fields.items():
            if key not in data:
                raise ValidationError(f"Unknown field: {key!r}")
            data[key] = value

        updated = Expense.from_dict(data)
        old = self._expenses[expense_id]
        if updated.expense_id != old.expense_id:
            raise ValidationError("Expense ID cannot be changed.")
        self._expenses[expense_id] = updated
        try:
            self._persist()
        except StorageError:
            self._expenses[expense_id] = old
            raise
        return updated

    def delete_expense(self, expense_id: str) -> Expense:
        """Remove an expense. Returns the deleted Expense; KeyError if missing."""
        expense = self._expenses.pop(expense_id)
        try:
            self._persist()
        except StorageError:
            self._expenses[expense_id] = expense
            raise
        return expense

    # -- queries ----------------------------------------------------------

    def total(self, expenses: Iterable[Expense] | None = None) -> Decimal:
        items = self.list_expenses() if expenses is None else list(expenses)
        return sum((e.amount for e in items), Decimal("0.00"))

    def expenses_in_month(self, year: int, month: int) -> list[Expense]:
        """Expenses whose date falls in the given year/month."""
        if not (1 <= month <= 12):
            raise ValidationError("Month must be between 1 and 12.")
        return [
            e
            for e in self.list_expenses()
            if e.expense_date.year == year and e.expense_date.month == month
        ]

    def monthly_summary(self, year: int, month: int) -> dict[str, Decimal | int]:
        """Total and per-category totals for a month."""
        items = self.expenses_in_month(year, month)
        by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for e in items:
            by_category[e.category] += e.amount
        return {
            "year": year,
            "month": month,
            "count": len(items),
            "total": self.total(items),
            "by_category": dict(by_category),
        }

    def category_summary(self) -> dict[str, dict[str, Decimal | int]]:
        """Per-category totals and counts across all expenses."""
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        counts: dict[str, int] = defaultdict(int)
        for e in self.list_expenses():
            totals[e.category] += e.amount
            counts[e.category] += 1
        return {
            category: {"total": totals[category], "count": counts[category]}
            for category in sorted(totals)
        }

    def all_categories(self) -> list[str]:
        """Sorted unique category names."""
        return sorted({e.category for e in self._expenses.values()})
