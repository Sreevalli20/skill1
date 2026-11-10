"""Expense data model and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

_DATE_FMT = "%Y-%m-%d"
_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")


class ValidationError(ValueError):
    """Raised when expense input fails validation."""


def parse_amount(value: Any) -> Decimal:
    """Parse a monetary value into a positive Decimal with 2dp quantization."""
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, bool):
        raise ValidationError("Amount must be a number, not a boolean.")
    elif isinstance(value, (int, float)):
        amount = Decimal(str(value))
    elif isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            raise ValidationError("Amount cannot be empty.")
        try:
            amount = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValidationError(f"Invalid amount: {value!r}") from exc
    else:
        raise ValidationError(f"Invalid amount type: {type(value).__name__}")

    if not amount.is_finite():
        raise ValidationError("Amount must be a finite number.")
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    return amount.quantize(Decimal("0.01"))


def parse_date(value: Any) -> date:
    """Parse a YYYY-MM-DD date string into a date."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), _DATE_FMT).date()
        except ValueError as exc:
            raise ValidationError(
                f"Invalid date {value!r}: expected YYYY-MM-DD."
            ) from exc
    raise ValidationError(f"Invalid date type: {type(value).__name__}")


def normalize_category(value: Any) -> str:
    """Normalize and validate a category name."""
    if not isinstance(value, str):
        raise ValidationError("Category must be a string.")
    category = " ".join(value.strip().split())
    if not category:
        raise ValidationError("Category cannot be empty.")
    if len(category) > 50:
        raise ValidationError("Category must be 50 characters or fewer.")
    return category


def normalize_description(value: Any) -> str:
    """Normalize and validate a description."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("Description must be a string.")
    description = " ".join(value.strip().split())
    if len(description) > 200:
        raise ValidationError("Description must be 200 characters or fewer.")
    return description


def generate_id(existing: set[str]) -> str:
    """Generate a unique expense ID based on the current timestamp."""
    import uuid

    while True:
        expense_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        if expense_id not in existing and _ID_RE.match(expense_id):
            return expense_id


@dataclass
class Expense:
    """A single expense record."""

    amount: Decimal
    category: str
    description: str = ""
    expense_date: date = field(default_factory=date.today)
    expense_id: str = ""

    def __post_init__(self) -> None:
        self.amount = parse_amount(self.amount)
        self.category = normalize_category(self.category)
        self.description = normalize_description(self.description)
        self.expense_date = parse_date(self.expense_date)
        if not self.expense_id:
            self.expense_id = generate_id(set())
        elif not _ID_RE.match(str(self.expense_id)):
            raise ValidationError(f"Invalid expense ID format: {self.expense_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.expense_id,
            "amount": str(self.amount),
            "category": self.category,
            "description": self.description,
            "date": self.expense_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Expense":
        try:
            return cls(
                amount=parse_amount(data["amount"]),
                category=data["category"],
                description=data.get("description", ""),
                expense_date=data["date"],
                expense_id=data.get("id", ""),
            )
        except KeyError as exc:
            raise ValidationError(f"Missing required field: {exc}") from exc
