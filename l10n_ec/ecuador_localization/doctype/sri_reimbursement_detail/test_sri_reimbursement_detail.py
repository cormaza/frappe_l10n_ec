"""Controller tests for SRI Reimbursement Detail (T1, in-memory dual-ring)."""

import unittest

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.doctype.sri_reimbursement_detail.sri_reimbursement_detail import (
	SRIReimbursementDetail,
)

if frappe is not None:
	EXPECTED_ERROR = (ValueError, frappe.ValidationError)
else:  # pragma: no cover
	EXPECTED_ERROR = ValueError


def _make_doc(**kwargs):
	base = {
		"doc_code": "01",
		"supplier_id_type": "04",
		"supplier_id": "1790016919001",
		"sri_number": "001-001-000000001",
		"issue_date": "2026-10-20",
		"auth_number": "1234567890",
		"base_amount": 100.0,
	}
	base.update(kwargs)
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Reimbursement Detail", **base})
	return SRIReimbursementDetail(**base)


class TestSRIReimbursementDetail(UnitTestCase):
	def test_controller_imports(self) -> None:
		doc = _make_doc()
		self.assertEqual(doc.doc_code, "01")
		self.assertEqual(float(doc.base_amount), 100.0)
