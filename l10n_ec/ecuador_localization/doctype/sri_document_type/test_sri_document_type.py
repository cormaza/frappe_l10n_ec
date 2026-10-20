import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_document_type.sri_document_type import (
	SRIDocumentType,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestSRIDocumentType(UnitTestCase):
	"""Unit tests for the SRI Document Type catalog DocType."""

	def test_codes_match_sri_specification(self) -> None:
		schema = json.loads(
			(Path(__file__).parent / "sri_document_type.json").read_text(encoding="utf-8")
		)
		code_field = next(f for f in schema["fields"] if f["fieldname"] == "code")
		self.assertEqual(
			set(code_field["options"].split("\n")), {"01", "03", "04", "05", "06", "07", "41"}
		)

	def test_controller_holds_code_and_title(self) -> None:
		doc = SRIDocumentType(code="01", title="Invoice")
		self.assertEqual(doc.code, "01")
		self.assertEqual(doc.title, "Invoice")
