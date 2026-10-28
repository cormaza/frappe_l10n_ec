"""Unit tests for received multi-invoice allocation guards (pure, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.received_batch import check_allocation, check_siblings


def _invoices(**overrides):
	base = {
		"SI-001": {
			"customer": "Demo Customer RUC",
			"company": "Demo Ecuador",
			"net_total": 1000.0,
			"iva_paid": 150.0,
			"ir_concepto": "303",
			"iva_concepto": "3",
			"settled": False,
			"referenced": False,
		},
		"SI-002": {
			"customer": "Demo Customer RUC",
			"company": "Demo Ecuador",
			"net_total": 500.0,
			"iva_paid": 75.0,
			"ir_concepto": "303",
			"iva_concepto": "",
			"settled": False,
			"referenced": False,
		},
	}
	base.update(overrides)
	return base


class TestAllocationGuards(UnitTestCase):
	def test_valid_split_passes(self) -> None:
		check_allocation({"sales_invoice": "SI-001", "ir_value": 100.0, "iva_value": 45.0}, _invoices())
		check_allocation({"sales_invoice": "SI-002", "ir_value": 50.0, "iva_value": 0.0}, _invoices())

	def test_unknown_invoice_fails(self) -> None:
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-XXX", "ir_value": 1.0}, _invoices())

	def test_settled_invoice_fails(self) -> None:
		invoices = _invoices()
		invoices["SI-001"]["settled"] = True
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "ir_value": 1.0}, invoices)

	def test_referenced_invoice_fails(self) -> None:
		invoices = _invoices()
		invoices["SI-001"]["referenced"] = True
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "ir_value": 1.0}, invoices)

	def test_ir_over_base_fails(self) -> None:
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "ir_value": 100.01}, _invoices())

	def test_ir_without_concepto_fails(self) -> None:
		invoices = _invoices()
		invoices["SI-001"]["ir_concepto"] = ""
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "ir_value": 10.0}, invoices)

	def test_iva_over_paid_fails(self) -> None:
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "iva_value": 150.01}, _invoices())

	def test_iva_without_concepto_fails(self) -> None:
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-002", "iva_value": 10.0}, _invoices())

	def test_empty_and_negative_fail(self) -> None:
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "ir_value": 0.0, "iva_value": 0.0}, _invoices())
		with self.assertRaises(ValueError):
			check_allocation({"sales_invoice": "SI-001", "ir_value": -5.0}, _invoices())


class TestSiblingUniformity(UnitTestCase):
	def test_mixed_customers_fail(self) -> None:
		invoices = _invoices()
		invoices["SI-002"]["customer"] = "Other Customer"
		with self.assertRaises(ValueError):
			check_siblings([{"sales_invoice": "SI-001"}, {"sales_invoice": "SI-002"}], invoices)

	def test_uniform_passes(self) -> None:
		check_siblings([{"sales_invoice": "SI-001"}, {"sales_invoice": "SI-002"}], _invoices())


class TestBatchTotalsNeverOverAllocate(unittest.TestCase):
	"""Edge pack E (S1/S2): one slip over three SIs never over-withholds.

	Rows are validated one by one today, so two rows on the same invoice
	each under the cap would pass while their sum exceeds it. The batch
	total guard sums IR/IVA per invoice and fails naming the invoice,
	while a mixed three-invoice batch within caps passes."""

	def _three(self):
		invoices = _invoices()
		invoices["SI-003"] = {
			"customer": "Demo Customer RUC",
			"company": "Demo Ecuador",
			"net_total": 2000.0,
			"iva_paid": 300.0,
			"ir_concepto": "303",
			"iva_concepto": "3",
			"settled": False,
			"referenced": False,
		}
		return invoices

	def test_mixed_three_invoice_batch_passes(self) -> None:
		from l10n_ec.ecuador_localization.received_batch import check_batch_totals

		allocations = [
			{"sales_invoice": "SI-001", "ir_value": 100.0, "iva_value": 45.0},
			{"sales_invoice": "SI-002", "ir_value": 50.0, "iva_value": 0.0},
			{"sales_invoice": "SI-003", "ir_value": 200.0, "iva_value": 300.0},
		]
		check_batch_totals(allocations, self._three())

	def test_split_ir_rows_cannot_exceed_cap_together(self) -> None:
		from l10n_ec.ecuador_localization.received_batch import check_batch_totals

		# SI-001 caps IR at 1000 x 10% = 100; each row alone passes.
		allocations = [
			{"sales_invoice": "SI-001", "ir_value": 60.0, "iva_value": 0.0},
			{"sales_invoice": "SI-001", "ir_value": 60.0, "iva_value": 0.0},
		]
		with self.assertRaises(ValueError) as ctx:
			check_batch_totals(allocations, self._three())
		self.assertIn("SI-001", str(ctx.exception))

	def test_split_iva_rows_cannot_exceed_paid_together(self) -> None:
		from l10n_ec.ecuador_localization.received_batch import check_batch_totals

		# SI-001 paid 150 IVA; each row alone passes.
		allocations = [
			{"sales_invoice": "SI-001", "ir_value": 0.0, "iva_value": 100.0},
			{"sales_invoice": "SI-001", "ir_value": 0.0, "iva_value": 60.0},
		]
		with self.assertRaises(ValueError) as ctx:
			check_batch_totals(allocations, self._three())
		self.assertIn("SI-001", str(ctx.exception))
