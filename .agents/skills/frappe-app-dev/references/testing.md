# Testing

## File location

Tests live alongside the DocType they test or in the app's `tests/` package:

- **Standalone App Repository Mode**:
  - DocType tests: `<app>/<module>/doctype/<doctype>/test_<doctype>.py`
  - App/domain tests: `<app>/tests/test_<feature>.py`
- **Full `frappe-bench` Mode**:
  - DocType tests: `apps/<app>/<app>/<module>/doctype/<doctype>/test_<doctype>.py`
  - App/domain tests: `apps/<app>/<app>/tests/test_<feature>.py`

## Mandatory Frappe v16 Test Runner Rule (`UnitTestCase` / `IntegrationTestCase`)

Frappe's `bench run-tests` uses `unittest.TestLoader().loadTestsFromModule(module)`, which **only** discovers methods on `unittest.TestCase` (`UnitTestCase` / `IntegrationTestCase`) subclasses and **silently ignores** bare top-level `def test_...()` functions.

- Every test in any `test_*.py` module **must** be a method inside a `UnitTestCase` or `IntegrationTestCase` class.
- Never write bare top-level `def test_...()` functions.
- To allow tests to run both in standalone `pytest` (Ring 1, without a live DB) and in `bench run-tests` (Ring 2), import `UnitTestCase` / `IntegrationTestCase` with a `unittest.TestCase` fallback:

```python
import unittest

try:
	from frappe.tests import IntegrationTestCase, UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]
	IntegrationTestCase = unittest.TestCase  # type: ignore[misc,assignment]
```

## Unit tests (no database — Ring 1 & Ring 2)

For pure domain logic, cryptographic signing, XML generation, or in-memory controller validation:

```python
class TestExpenseUtils(UnitTestCase):
	def test_calculate_tax(self) -> None:
		self.assertEqual(calculate_tax(100, 0.1), 10)
```

`UnitTestCase` runs in sub-second time with no DB setup/teardown.

## Integration tests (database-backed — Ring 2)

```python
import frappe
from frappe.tests import IntegrationTestCase


class TestExpense(IntegrationTestCase):
	def test_expense_creation(self) -> None:
		doc = frappe.get_doc(doctype="Expense", title="Test", amount=100)
		doc.insert()
		self.assertEqual(doc.amount, 100)

	def test_validation(self) -> None:
		doc = frappe.get_doc(doctype="Expense", title="Test", amount=-1)
		self.assertRaises(frappe.ValidationError, doc.insert)
```

## Running tests

### Ring 1: Fast Local TDD Loop (Standalone App Repo, No DB required)

```bash
# Run all UnitTestCase suites across <app>/tests and <app>/<module>/doctype/*/test_*.py
.venv/bin/pytest -v --cov=l10n_ec/sri --cov-report=term-missing -W error

# Run full GitHub Actions fast-tdd-unit job locally in Docker via act
act workflow_dispatch -W .github/workflows/ci.yml -j fast-tdd-unit
```

### Ring 2: Full `frappe-bench` / Containerized Integration

Always run `bench run-tests` on a dedicated test site (`test_site`), never on an active development site:

```bash
# All tests for an app
bench --site test_site run-tests --app <app-name>

# Specific DocType
bench --site test_site run-tests --doctype "SRI Signature"

# Specific test module
bench --site test_site run-tests --module <app>.<module>.doctype.<doctype>.test_<doctype>

# Specific test method
bench --site test_site run-tests --module <app>.<module>.doctype.<doctype>.test_<doctype> --test test_validate_and_sign_controller
```

## Common pitfalls

- Writing bare `def test_foo():` functions: `pytest` runs them, but `bench run-tests` silently skips them. Always wrap test methods inside a `UnitTestCase` or `IntegrationTestCase` class.
- If integration tests fail with "DocType not found", run `bench --site <site> migrate` first.
- Test files must be named `test_*.py` to be discovered.
