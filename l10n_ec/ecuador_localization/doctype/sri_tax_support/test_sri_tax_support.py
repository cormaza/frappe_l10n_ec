import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_tax_support.sri_tax_support import (
	SRITaxSupport,
)

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _make_doc(**kwargs):
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Tax Support", **kwargs})
	return SRITaxSupport(**kwargs)


class TestSRITaxSupport(UnitTestCase):
	"""Unit tests for the SRI Tax Support catalog DocType."""

	def test_codes_match_sri_specification(self) -> None:
		schema = json.loads((Path(__file__).parent / "sri_tax_support.json").read_text(encoding="utf-8"))
		code_field = next(f for f in schema["fields"] if f["fieldname"] == "code")
		self.assertEqual(
			set(code_field["options"].split("\n")),
			{f"{n:02d}" for n in range(1, 16)},
		)

	def test_controller_holds_code_and_title(self) -> None:
		doc = _make_doc(code="01", title="VAT Tax Credit")
		self.assertEqual(doc.code, "01")
		self.assertEqual(doc.title, "VAT Tax Credit")

	def test_link_shows_title_with_code(self) -> None:
		schema = json.loads((Path(__file__).parent / "sri_tax_support.json").read_text(encoding="utf-8"))
		self.assertEqual(schema.get("title_field"), "title")
		self.assertEqual(schema.get("show_title_field_in_link"), 1)
