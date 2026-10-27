"""Controller tests for SRI Import Assumption (T7, dual-ring)."""

import unittest

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.doctype.sri_import_assumption.sri_import_assumption import (
	SRIImportAssumption,
)

if frappe is not None:
	EXPECTED_ERROR = (ValueError, frappe.ValidationError)
else:  # pragma: no cover
	EXPECTED_ERROR = ValueError


def _make_doc(**kwargs):
	base = {
		"company": "Demo Ecuador",
		"item_code": "DEMO-WIDGET",
		"partida": "8504409090",
		"ad_valorem_rate": 10.0,
		"source_dai": "123-2026-10-000002",
	}
	base.update(kwargs)
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Import Assumption", **base})
	return SRIImportAssumption(**base)


class TestSRIImportAssumption(UnitTestCase):
	def test_valid_assumption_passes(self) -> None:
		doc = _make_doc()
		if frappe is None:
			doc.validate()
		self.assertEqual(doc.partida, "8504409090")

	def test_bad_partida_fails(self) -> None:
		doc = _make_doc(partida="8504.40")
		with self.assertRaises(EXPECTED_ERROR):
			doc.validate()

	def test_missing_partida_fails(self) -> None:
		doc = _make_doc(partida=None)
		with self.assertRaises(EXPECTED_ERROR):
			doc.validate()
