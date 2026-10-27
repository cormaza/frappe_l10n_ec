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
