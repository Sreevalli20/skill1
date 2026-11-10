# Personal Expense Tracker

A simple, modular, command-line Personal Expense Tracker developed using Python 3.14.6. The application helps users record, manage, and analyze their daily expenses with persistent JSON storage.

## Features

- Add new expenses with amount, category, description, and date.
- View all recorded expenses.
- Update existing expense records.
- Delete expenses with confirmation.
- Validate expense amounts and dates.
- Calculate total expenditure.
- Generate category-wise expense summaries.
- Generate monthly expense summaries.
- Track expenses using accurate `Decimal` arithmetic.
- Save and retrieve expense records using JSON.
- Handle invalid inputs and corrupted storage files.
- Atomic file writes for safer data persistence.

## Technology Stack

- Python 3.14.6
- JSON
- `decimal.Decimal`
- `datetime`
- `pathlib`
- `unittest`

**Dependencies: None.** Uses Python's standard library only.

## Project Architecture

```text
skill1/
│
├── main.py
├── expense_tracker/
│   ├── __init__.py
│   ├── expense.py
│   ├── storage.py
│   ├── tracker.py
│   └── cli.py
│
├── tests/
│   └── test_expense_tracker.py
│
└── README.md
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `main.py` | Application entry point |
| `expense.py` | Expense model and validation |
| `storage.py` | JSON storage and persistence |
| `tracker.py` | Expense CRUD operations and calculations |
| `cli.py` | Interactive command-line interface |
| `test_expense_tracker.py` | Automated unit tests |
| `README.md` | Project documentation |

## Requirements

- Python 3.14.6
- No external dependencies.

## Installation and Execution

Clone the repository:

```bash
git clone https://github.com/Sreevalli20/skill1.git
```

Navigate into the project:

```bash
cd skill1
```

Check Python version:

```bash
python --version
```

Expected version:

```text
Python 3.14.6
```

Run the application:

```bash
python main.py
```

## Application Menu

1. Add Expense
2. View All Expenses
3. Update Expense
4. Delete Expense
5. View Expense Summary
6. Category-wise Report
7. Exit

## Testing

Run the automated unit tests:

```bash
python -m unittest discover -s tests -v
```

The project passes **19 unit tests** under Python 3.14.6.

## Data Storage

Expense records are stored in `expenses.json` in the working directory.
The application uses Decimal-based monetary calculations and stores monetary values as strings to preserve precision.

## Limitations

- Designed for single-user usage.
- Uses local JSON file storage.
- Expense amounts must be positive.
- Dates use `YYYY-MM-DD` format.
- Stored financial data is not encrypted.

## Academic Project

- **Course:** Python Programming – Week 1
- **Project:** Personal Expense Tracker
- **Language:** Python 3.14.6
- **Repository:** https://github.com/Sreevalli20/skill1
