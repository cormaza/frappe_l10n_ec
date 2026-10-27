"""Controller tests for SRI Import Settlement (T2: link set, dual-ring)."""

import unittest

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.doctype.sri_import_settlement.sri_import_settlement import (
	SRIImportSettlement,
)

if frappe is not None:
	EXPECTED_ERROR = (ValueError, frappe.ValidationError)
else:  # pragma: no cover
	EXPECTED_ERROR = ValueError


def _make_doc(**kwargs):
	base = {
		"company": "Demo Ecuador",
		"supplier": "Demo Foreign Co",
		"purchase_invoice": "ACC-PINV-2026-00001",
	}
	base.update(kwargs)
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Import Settlement", **base})
	return SRIImportSettlement(**base)


class TestSRIImportSettlementLinks(UnitTestCase):
	def test_goods_invoice_passes_pure_checks(self) -> None:
		doc = _make_doc()
		if frappe is None:
			doc.validate()
		self.assertEqual(doc.purchase_invoice, "ACC-PINV-2026-00001")

	def test_missing_company_fails(self) -> None:
		doc = _make_doc(company=None)
		with self.assertRaises(EXPECTED_ERROR):
			doc.validate()

	def test_no_goods_source_fails(self) -> None:
		doc = _make_doc(
			purchase_invoice=None,
			freight_invoice="ACC-PINV-2026-00002",
		)
		with self.assertRaises(EXPECTED_ERROR):
			doc.validate()

	def test_same_document_in_two_roles_fails(self) -> None:
		doc = _make_doc(freight_invoice="ACC-PINV-2026-00001")
		with self.assertRaises(EXPECTED_ERROR):
			doc.validate()


class TestSRIImportSettlementCompute(UnitTestCase):
	def _costs(self):
		return {"fob": 1000.0, "freight": 200.0, "insurance": 50.0}

	def _rates(self):
		return {"ad_valorem": 10.0, "fodinfa": 0.5, "iva": 15.0}

	def _declared(self):
		return {
			"dai_ad_valorem": 125.0,
			"dai_fodinfa": 6.25,
			"dai_iva": 207.19,
			"dai_total": 338.44,
		}

	def test_settle_from_stamps_computed_totals(self) -> None:
		doc = _make_doc()
		computed = doc.settle_from(self._costs(), self._rates(), self._declared())
		self.assertEqual(computed["cif"], 1250.0)
		self.assertEqual(doc.cif_total, 1250.0)
		self.assertEqual(doc.iva_amount, 207.19)

	def test_settle_from_without_rates_returns_empty(self) -> None:
		doc = _make_doc()
		self.assertEqual(doc.settle_from(self._costs(), {}, {}), {})
		self.assertIsNone(getattr(doc, "cif_total", None))

	def test_settle_from_mismatch_fails(self) -> None:
		doc = _make_doc()
		declared = dict(self._declared(), dai_ad_valorem=250.0)
		with self.assertRaises(EXPECTED_ERROR):
			doc.settle_from(self._costs(), self._rates(), declared)

	def test_apply_declaration_csv_stamps_form_fields(self) -> None:
		doc = _make_doc()
		csv_text = (
			"dai_number,dai_date,ad_valorem_rate,fodinfa_rate,iva_rate,"
			"ice,other_duties,dai_ad_valorem,dai_fodinfa,dai_iva,dai_total\n"
			"123-2026-10-000001,2026-10-15,10.0,0.5,15.0,0.0,0.0,125.0,6.25,207.19,338.44"
		)
		doc.apply_declaration_csv(csv_text)
		self.assertEqual(doc.dai_number, "123-2026-10-000001")
		self.assertEqual(doc.ad_valorem_rate, 10.0)
		self.assertEqual(doc.dai_iva, 207.19)

	def test_apply_declaration_csv_bad_file_fails(self) -> None:
		doc = _make_doc()
		with self.assertRaises(EXPECTED_ERROR):
			doc.apply_declaration_csv("fobola\n1")


class TestSRIImportSettlementLandedCost(UnitTestCase):
	def test_duplicate_landed_cost_fails(self) -> None:
		doc = _make_doc(landed_cost_voucher="MAT-LCV-2026-00001")
		with self.assertRaises(EXPECTED_ERROR) as ctx:
			doc.make_landed_cost_voucher()
		self.assertIn("already costed", str(ctx.exception))

	def test_without_receipt_fails(self) -> None:
		doc = _make_doc(purchase_invoice=None, purchase_receipt=None, purchase_order="PO-2026-00001")
		with self.assertRaises(EXPECTED_ERROR):
			doc.make_landed_cost_voucher()
