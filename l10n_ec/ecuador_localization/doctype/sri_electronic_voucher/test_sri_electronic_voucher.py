import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_electronic_voucher.sri_electronic_voucher import (
	SRIElectronicVoucher,
)

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _make_doc(**kwargs):
	values = {
		"access_key": "2410202601179001691900110010010000000011234567815",
		"voucher_state": "Generated",
		"sri_doc_code": "01",
		"company": "Demo Ecuador",
		"reference_doctype": "Sales Invoice",
		"reference_name": "ACC-SINV-2026-00001",
	}
	values.update(kwargs)
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Electronic Voucher", **values})
	return SRIElectronicVoucher(**values)


class TestSRIElectronicVoucher(UnitTestCase):
	"""Unit tests for the SRI Electronic Voucher DocType (no database)."""

	def test_states_match_machine(self) -> None:
		schema = json.loads(
			(Path(__file__).parent / "sri_electronic_voucher.json").read_text(encoding="utf-8")
		)
		state_field = next(f for f in schema["fields"] if f["fieldname"] == "voucher_state")
		self.assertEqual(
			set(state_field["options"].split("\n")),
			{"Generated", "Signed", "Received", "Authorized", "Returned", "Rejected"},
		)
		code_field = next(f for f in schema["fields"] if f["fieldname"] == "sri_doc_code")
		self.assertEqual(set(code_field["options"].split("\n")), {"01", "03", "04", "05"})

	def test_controller_holds_key_and_state(self) -> None:
		doc = _make_doc()
		self.assertEqual(doc.voucher_state, "Generated")
		self.assertEqual(doc.sri_doc_code, "01")
