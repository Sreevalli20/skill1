"""Command-line interface for the Personal Expense Tracker."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from .expense import ValidationError, parse_amount, parse_date
from .storage import ExpenseStore, StorageError
from .tracker import ExpenseTracker


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value if value else (default or "")


def _prompt_amount() -> Decimal:
    while True:
        raw = input("Amount: ").strip()
        try:
            return parse_amount(raw)
        except ValidationError as exc:
            print(f"  Invalid amount: {exc}")


def _prompt_date(default: date | None = None) -> date | None:
    hint = default.isoformat() if default else date.today().isoformat()
    while True:
        raw = input(f"Date (YYYY-MM-DD) [{hint}]: ").strip()
        if not raw:
            return default
        try:
            return parse_date(raw)
        except ValidationError as exc:
            print(f"  Invalid date: {exc}")


def _choose_expense(tracker: ExpenseTracker) -> str | None:
    expenses = tracker.list_expenses()
    if not expenses:
        print("No expenses recorded.")
        return None
    for i, e in enumerate(expenses, 1):
        print(f"  {i}. [{e.expense_id}] {e.expense_date}  "
              f"{e.category:<15} {e.amount:>10}  {e.description}")
    while True:
        raw = input("Enter number or expense ID (blank to cancel): ").strip()
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(expenses):
            return expenses[int(raw) - 1].expense_id
        if tracker.get_expense(raw):
            return raw
        print("  Invalid selection.")


def add_expense(tracker: ExpenseTracker) -> None:
    print("\n--- Add Expense ---")
    amount = _prompt_amount()
    category = _prompt("Category")
    if not category:
        print("  Category is required.")
        return
    description = _prompt("Description (optional)")
    expense_date = _prompt_date()
    try:
        expense = tracker.add_expense(amount, category, description, expense_date)
        print(f"  Added expense {expense.expense_id}: {expense.amount} for {expense.category}")
    except (ValidationError, StorageError) as exc:
        print(f"  Error: {exc}")


def view_expenses(tracker: ExpenseTracker) -> None:
    print("\n--- Expenses ---")
    expenses = tracker.list_expenses()
    if not expenses:
        print("  No expenses recorded.")
        return
    for e in expenses:
        print(f"  [{e.expense_id}] {e.expense_date}  {e.category:<15} "
              f"{e.amount:>10}  {e.description}")
    noun = "expense" if len(expenses) == 1 else "expenses"
    print(f"  {'TOTAL':<15} {'':>10}  {tracker.total():>10}  ({len(expenses)} {noun})")


def update_expense(tracker: ExpenseTracker) -> None:
    print("\n--- Update Expense ---")
    expense_id = _choose_expense(tracker)
    if not expense_id:
        return
    expense = tracker.get_expense(expense_id)
    assert expense is not None
    print(f"Current: {expense.expense_date}  {expense.category}  "
          f"{expense.amount}  {expense.description}")

    fields: dict[str, object] = {}
    raw_amount = _prompt("New amount (blank to keep)", str(expense.amount))
    if raw_amount != str(expense.amount):
        fields["amount"] = raw_amount
    new_cat = _prompt("New category (blank to keep)", expense.category)
    if new_cat != expense.category:
        fields["category"] = new_cat
    new_desc = _prompt("New description (blank to keep)", expense.description or "")
    if new_desc != expense.description:
        fields["description"] = new_desc
    new_date = _prompt_date(expense.expense_date)
    if new_date != expense.expense_date:
        fields["date"] = new_date

    if not fields:
        print("  Nothing changed.")
        return
    try:
        tracker.update_expense(expense_id, **fields)
        print("  Expense updated.")
    except (ValidationError, StorageError, KeyError) as exc:
        print(f"  Error: {exc}")


def delete_expense(tracker: ExpenseTracker) -> None:
    print("\n--- Delete Expense ---")
    expense_id = _choose_expense(tracker)
    if not expense_id:
        return
    confirm = input("Delete this expense? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return
    try:
        tracker.delete_expense(expense_id)
        print("  Expense deleted.")
    except (StorageError, KeyError) as exc:
        print(f"  Error: {exc}")


def category_summary(tracker: ExpenseTracker) -> None:
    print("\n--- Category Summary ---")
    summary = tracker.category_summary()
    if not summary:
        print("  No expenses recorded.")
        return
    for category, info in summary.items():
        noun = "expense" if info["count"] == 1 else "expenses"
        print(f"  {category:<20} {info['count']:>4} {noun:<9}  {info['total']:>12}")
    print(f"  {'GRAND TOTAL':<20} {'':>4}  {tracker.total():>12}")


def monthly_summary(tracker: ExpenseTracker) -> None:
    print("\n--- Monthly Summary ---")
    today = date.today()
    while True:
        raw = input(f"Month (YYYY-MM) [{today:%Y-%m}]: ").strip()
        if not raw:
            year, month = today.year, today.month
            break
        try:
            year_s, month_s = raw.split("-", 1)
            year, month = int(year_s), int(month_s)
            if not (1 <= month <= 12):
                raise ValueError
            break
        except ValueError:
            print("  Invalid month. Use YYYY-MM.")
    summary = tracker.monthly_summary(year, month)
    print(f"  {year}-{month:02d}: {summary['count']} expenses, "
          f"total {summary['total']}")
    for category, total in sorted(summary["by_category"].items()):
        print(f"    {category:<20} {total}")


def run(store_path: str = "expenses.json") -> None:
    try:
        tracker = ExpenseTracker(ExpenseStore(store_path))
    except StorageError as exc:
        print(f"Failed to load data: {exc}")
        return

    menu = """
========== EXPENSE TRACKER ==========
  1. Add expense
  2. View expenses
  3. Update expense
  4. Delete expense
  5. Category summary
  6. Monthly summary
  7. Exit
====================================="""
    while True:
        print(menu)
        try:
            choice = input("Choose an option: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        try:
            if choice == "1":
                add_expense(tracker)
            elif choice == "2":
                view_expenses(tracker)
            elif choice == "3":
                update_expense(tracker)
            elif choice == "4":
                delete_expense(tracker)
            elif choice == "5":
                category_summary(tracker)
            elif choice == "6":
                monthly_summary(tracker)
            elif choice == "7":
                print("Goodbye!")
                break
            else:
                print("  Invalid option.")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


def main() -> None:
    run()


if __name__ == "__main__":
    main()
