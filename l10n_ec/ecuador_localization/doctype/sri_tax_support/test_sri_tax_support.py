import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_tax_support.sri_tax_support import (
	SRITaxSupport,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


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
		doc = SRITaxSupport(code="01", title="VAT Tax Credit")
		self.assertEqual(doc.code, "01")
		self.assertEqual(doc.title, "VAT Tax Credit")
