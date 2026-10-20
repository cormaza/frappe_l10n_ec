import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_identification_type.sri_identification_type import (
	SRIIdentificationType,
)

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _make_doc(**kwargs):
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Identification Type", **kwargs})
	return SRIIdentificationType(**kwargs)


class TestSRIIdentificationType(UnitTestCase):
	"""Unit tests for the SRI Identification Type catalog DocType."""

	def test_codes_match_sri_specification(self) -> None:
		schema = json.loads(
			(Path(__file__).parent / "sri_identification_type.json").read_text(encoding="utf-8")
		)
		code_field = next(f for f in schema["fields"] if f["fieldname"] == "code")
		self.assertEqual(set(code_field["options"].split("\n")), {"04", "05", "06", "07", "08"})

	def test_controller_holds_code_and_title(self) -> None:
		doc = _make_doc(code="04", title="RUC")
		self.assertEqual(doc.code, "04")
		self.assertEqual(doc.title, "RUC")

	def test_link_shows_title_with_code(self) -> None:
		schema = json.loads(
			(Path(__file__).parent / "sri_identification_type.json").read_text(encoding="utf-8")
		)
		self.assertEqual(schema.get("title_field"), "title")
		self.assertEqual(schema.get("show_title_field_in_link"), 1)
