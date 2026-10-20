import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_payment_method.sri_payment_method import (
	SRIPaymentMethod,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestSRIPaymentMethod(UnitTestCase):
	"""Unit tests for the SRI Payment Method catalog DocType."""

	def test_codes_match_sri_specification(self) -> None:
		schema = json.loads(
			(Path(__file__).parent / "sri_payment_method.json").read_text(encoding="utf-8")
		)
		code_field = next(f for f in schema["fields"] if f["fieldname"] == "code")
		self.assertEqual(
			set(code_field["options"].split("\n")),
			{"01", "15", "16", "17", "18", "19", "20", "21"},
		)

	def test_controller_holds_code_and_title(self) -> None:
		doc = SRIPaymentMethod(code="19", title="Credit Card")
		self.assertEqual(doc.code, "19")
		self.assertEqual(doc.title, "Credit Card")
