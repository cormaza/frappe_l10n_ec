"""Unit tests for the automatic IVA withholding deduction row (ERPNext gap)."""

import unittest

from l10n_ec.ecuador_localization.validation import enforce_iva_deduction_row

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class FakeRow:
	"""Child-row double supporting `.get`, attribute access, and assignment."""

	def __init__(self, values: dict) -> None:
		self.__dict__.update(values)

	def get(self, key, default=None):
		return self.__dict__.get(key, default)

	def __getitem__(self, key):
		return self.__dict__[key]


class FakePI(dict):
	"""Purchase-Invoice double with appendable taxes and a calculate spy."""

	def __init__(self, values: dict) -> None:
		super().__init__(values)
		self.calculated = 0

	def append(self, fieldname: str, row: dict):
		fake = FakeRow(dict(row, idx=len(self[fieldname]) + 1))
		self[fieldname].append(fake)
		return fake

	def calculate_taxes_and_totals(self) -> None:
		self.calculated += 1


def _doc(**overrides) -> FakePI:
	base = {
		"company": "Demo Ecuador",
		"sri_iva_concepto": "1",
		"taxes": [FakeRow({"idx": 1, "account_head": "VAT", "tax_amount": 15.0})],
	}
	base.update(overrides)
	return FakePI(base)


class TestIvaDeductionRow(UnitTestCase):
	def test_appends_deduction_row_and_recalculates(self) -> None:
		doc = _doc()
		enforce_iva_deduction_row(doc, company_code="EC", resolve_account=lambda company: "2010708 - WH")
		self.assertEqual(len(doc["taxes"]), 2)
		row = doc["taxes"][1]
		self.assertEqual(row.charge_type, "On Previous Row Amount")
		self.assertEqual(row.add_deduct_tax, "Deduct")
		self.assertEqual(row.rate, 30.0)
		self.assertEqual(row.row_id, "1")
		self.assertEqual(row.account_head, "2010708 - WH")
		self.assertEqual(doc.calculated, 1)

	def test_existing_row_is_updated_not_doubled(self) -> None:
		doc = _doc(
			taxes=[
				FakeRow({"idx": 1, "account_head": "VAT", "tax_amount": 15.0}),
				FakeRow(
					{
						"idx": 2,
						"account_head": "2010708 - WH",
						"add_deduct_tax": "Deduct",
						"rate": 70.0,
						"row_id": "1",
						"tax_amount": 10.5,
					}
				),
			]
		)
		enforce_iva_deduction_row(doc, company_code="EC", resolve_account=lambda company: "2010708 - WH")
		self.assertEqual(len(doc["taxes"]), 2)
		self.assertEqual(doc["taxes"][1].rate, 30.0)

	def test_empty_concepto_skips(self) -> None:
		doc = _doc(sri_iva_concepto="")
		enforce_iva_deduction_row(doc, company_code="EC")
		self.assertEqual(len(doc["taxes"]), 1)
		self.assertEqual(doc.calculated, 0)

	def test_non_ecuadorian_company_skips(self) -> None:
		doc = _doc()
		enforce_iva_deduction_row(doc, company_code="CO")
		self.assertEqual(len(doc["taxes"]), 1)

	def test_unknown_concepto_raises(self) -> None:
		with self.assertRaises(ValueError):
			enforce_iva_deduction_row(_doc(sri_iva_concepto="9999"), company_code="EC")

	def test_non_iva_concepto_raises(self) -> None:
		with self.assertRaises(ValueError):
			enforce_iva_deduction_row(_doc(sri_iva_concepto="303"), company_code="EC")

	def test_concepto_without_iva_taxes_raises(self) -> None:
		with self.assertRaises(ValueError):
			enforce_iva_deduction_row(_doc(taxes=[]), company_code="EC")

	def test_multiple_iva_rows_raise(self) -> None:
		doc = _doc(
			taxes=[
				FakeRow({"idx": 1, "account_head": "VAT-A", "tax_amount": 15.0}),
				FakeRow({"idx": 2, "account_head": "VAT-B", "tax_amount": 5.0}),
			]
		)
		with self.assertRaises(ValueError):
			enforce_iva_deduction_row(doc, company_code="EC")

	def test_missing_account_raises(self) -> None:
		with self.assertRaises(ValueError):
			enforce_iva_deduction_row(_doc(), company_code="EC", resolve_account=lambda c: None)


if __name__ == "__main__":
	unittest.main()
