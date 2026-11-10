"""Tests for the Personal Expense Tracker. Run: python -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_tracker.expense import Expense, ValidationError, parse_amount, parse_date
from expense_tracker.storage import ExpenseStore, StorageError
from expense_tracker.tracker import ExpenseTracker


class ParseAmountTests(unittest.TestCase):
    def test_valid_amounts(self):
        self.assertEqual(parse_amount("10.50"), Decimal("10.50"))
        self.assertEqual(parse_amount("1,234.56"), Decimal("1234.56"))
        self.assertEqual(parse_amount(7), Decimal("7.00"))
        self.assertEqual(parse_amount(0.1), Decimal("0.10"))

    def test_invalid_amounts(self):
        for bad in ["abc", "", "-5", "0", "0.00", True, None, [1]]:
            with self.assertRaises(ValidationError, msg=f"amount={bad!r}"):
                parse_amount(bad)

    def test_float_precision(self):
        # 0.1 + 0.2 style float issues must not appear with Decimal
        a = parse_amount("0.10")
        b = parse_amount("0.20")
        self.assertEqual(a + b, Decimal("0.30"))


class ParseDateTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_date("2026-11-10"), date(2026, 11, 10))
        self.assertEqual(parse_date(date(2026, 1, 1)), date(2026, 1, 1))

    def test_invalid(self):
        for bad in ["10/11/2026", "2026-13-01", "not-a-date", 12345]:
            with self.assertRaises(ValidationError, msg=f"date={bad!r}"):
                parse_date(bad)


class ExpenseTests(unittest.TestCase):
    def test_defaults_and_serialization(self):
        e = Expense(amount="12.34", category="  Food   Shopping ", description=" lunch ")
        self.assertEqual(e.amount, Decimal("12.34"))
        self.assertEqual(e.category, "Food Shopping")
        self.assertEqual(e.description, "lunch")
        self.assertEqual(e.expense_date, date.today())
        self.assertTrue(e.expense_id)

        e2 = Expense.from_dict(e.to_dict())
        self.assertEqual(e2.to_dict(), e.to_dict())

    def test_validation_errors(self):
        with self.assertRaises(ValidationError):
            Expense(amount="-1", category="Food")
        with self.assertRaises(ValidationError):
            Expense(amount="5", category="")
        with self.assertRaises(ValidationError):
            Expense(amount="5", category="x" * 60)
        with self.assertRaises(ValidationError):
            Expense(amount="5", category="Food", expense_date="bad")


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ExpenseStore(Path(self.tmp.name) / "expenses.json")
        self.tracker = ExpenseTracker(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_and_list(self):
        e1 = self.tracker.add_expense("10.00", "Food", "lunch", "2026-11-01")
        e2 = self.tracker.add_expense("20.50", "Transport", "cab", "2026-11-05")
        self.assertEqual(len(self.tracker.list_expenses()), 2)
        # sorted by date descending
        self.assertEqual(self.tracker.list_expenses()[0].expense_id, e2.expense_id)
        self.assertEqual(self.tracker.list_expenses()[1].expense_id, e1.expense_id)

    def test_total_decimal_accuracy(self):
        self.tracker.add_expense("0.10", "A")
        self.tracker.add_expense("0.20", "A")
        self.assertEqual(self.tracker.total(), Decimal("0.30"))

    def test_update(self):
        e = self.tracker.add_expense("10.00", "Food", "lunch", "2026-11-01")
        updated = self.tracker.update_expense(
            e.expense_id, amount="15.25", category="Dining", date="2026-11-02"
        )
        self.assertEqual(updated.amount, Decimal("15.25"))
        self.assertEqual(updated.category, "Dining")
        self.assertEqual(updated.expense_date, date(2026, 11, 2))
        self.assertEqual(updated.expense_id, e.expense_id)

    def test_update_errors(self):
        with self.assertRaises(KeyError):
            self.tracker.update_expense("nonexistent", amount="1")
        e = self.tracker.add_expense("10.00", "Food")
        with self.assertRaises(ValidationError):
            self.tracker.update_expense(e.expense_id, bogus_field="x")
        with self.assertRaises(ValidationError):
            self.tracker.update_expense(e.expense_id, amount="-5")
        with self.assertRaises(ValidationError):
            self.tracker.update_expense(e.expense_id, id="tampered")

    def test_delete(self):
        e = self.tracker.add_expense("10.00", "Food")
        deleted = self.tracker.delete_expense(e.expense_id)
        self.assertEqual(deleted.expense_id, e.expense_id)
        with self.assertRaises(KeyError):
            self.tracker.delete_expense(e.expense_id)

    def test_add_invalid_rolls_back(self):
        with self.assertRaises(ValidationError):
            self.tracker.add_expense("-5", "Food")
        self.assertEqual(len(self.tracker.list_expenses()), 0)

    def test_persistence_roundtrip(self):
        self.tracker.add_expense("12.34", "Food", "lunch", "2026-11-01")
        self.tracker.add_expense("56.78", "Bills", "electricity", "2026-11-03")

        # Simulate restart: brand-new tracker over the same file
        tracker2 = ExpenseTracker(self.store)
        self.assertEqual(len(tracker2.list_expenses()), 2)
        self.assertEqual(tracker2.total(), Decimal("69.12"))

    def test_corrupt_file(self):
        self.store.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(StorageError):
            ExpenseTracker(self.store)

    def test_missing_fields_in_file(self):
        self.store.path.write_text(
            json.dumps({"expenses": [{"id": "x"}]}), encoding="utf-8"
        )
        with self.assertRaises(StorageError):
            ExpenseTracker(self.store)

    def test_category_summary(self):
        self.tracker.add_expense("10.00", "Food", expense_date="2026-11-01")
        self.tracker.add_expense("5.00", "Food", expense_date="2026-11-02")
        self.tracker.add_expense("20.00", "Transport", expense_date="2026-11-03")
        summary = self.tracker.category_summary()
        self.assertEqual(summary["Food"]["total"], Decimal("15.00"))
        self.assertEqual(summary["Food"]["count"], 2)
        self.assertEqual(summary["Transport"]["total"], Decimal("20.00"))
        self.assertEqual(self.tracker.all_categories(), ["Food", "Transport"])

    def test_monthly_summary(self):
        self.tracker.add_expense("10.00", "Food", expense_date="2026-11-01")
        self.tracker.add_expense("20.00", "Food", expense_date="2026-11-30")
        self.tracker.add_expense("99.00", "Food", expense_date="2026-10-15")
        summary = self.tracker.monthly_summary(2026, 11)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["total"], Decimal("30.00"))
        self.assertEqual(summary["by_category"]["Food"], Decimal("30.00"))

    def test_monthly_summary_bad_month(self):
        with self.assertRaises(ValidationError):
            self.tracker.monthly_summary(2026, 13)


if __name__ == "__main__":
    unittest.main()
