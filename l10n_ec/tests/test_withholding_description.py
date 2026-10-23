"""Unit tests for withholding description rate fallback (no database)."""

import unittest
from types import SimpleNamespace

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.validation import sync_tax_row_descriptions


def _doc(*rows, category="Ecuador IR 2%"):
	return SimpleNamespace(
		get=lambda key, default=None: {
			"company": "Demo Ecuador",
			"taxes": list(rows),
			"items": [],
			"tax_withholding_category": category,
		}.get(key, default),
	)


def _row(head, rate, amount):
	ns = SimpleNamespace(account_head=head, rate=rate, tax_amount=amount, description="")
	ns.get = lambda key, default=None: getattr(ns, key, default)
	return ns


class TestWithholdingDescriptionRate(UnitTestCase):
	def test_zero_rate_resolves_from_category(self) -> None:
		row = _row("2010709 - RETENCIÓN DE IR POR PAGAR - DE", 0.0, 2.0)
		sync_tax_row_descriptions(_doc(row), None, company_code="EC", resolve_category_rate=lambda _name: 2.0)
		self.assertEqual(row.description, "Ret. IR 2%")

	def test_ambiguous_category_keeps_row_rate(self) -> None:
		row = _row("2010709 - RETENCIÓN DE IR POR PAGAR - DE", 0.0, 2.0)
		sync_tax_row_descriptions(
			_doc(row), None, company_code="EC", resolve_category_rate=lambda _name: None
		)
		self.assertEqual(row.description, "Ret. IR 0%")

	def test_nonzero_rate_ignores_category(self) -> None:
		row = _row("2010709 - RETENCIÓN DE IR POR PAGAR - DE", 2.0, 2.0)
		sync_tax_row_descriptions(_doc(row), None, company_code="EC", resolve_category_rate=lambda _name: 8.0)
		self.assertEqual(row.description, "Ret. IR 2%")
