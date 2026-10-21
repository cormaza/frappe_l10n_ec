import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.doctype.sri_additional_information.sri_additional_information import (
	SRIAdditionalInformation,
)

try:
	import frappe
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _make_doc(**kwargs):
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Additional Information", **kwargs})
	return SRIAdditionalInformation(**kwargs)


class TestSRIAdditionalInformation(UnitTestCase):
	"""Unit tests for the central infoAdicional DocType."""

	def test_schema_holds_company_scoped_entries(self) -> None:
		schema = json.loads(
			(Path(__file__).parent / "sri_additional_information.json").read_text(encoding="utf-8")
		)
		by_name = {f["fieldname"]: f for f in schema["fields"]}
		self.assertEqual(by_name["company"]["fieldtype"], "Link")
		self.assertEqual(by_name["company"]["options"], "Company")
		self.assertEqual(by_name["enabled"]["fieldtype"], "Check")
		self.assertEqual(by_name["entries"]["fieldtype"], "Table")
		self.assertEqual(by_name["entries"]["options"], "SRI Additional Information Entry")

	def test_child_schema_holds_nombre_valor(self) -> None:
		schema = json.loads(
			(
				Path(__file__).parent.parent
				/ "sri_additional_information_entry"
				/ "sri_additional_information_entry.json"
			).read_text(encoding="utf-8")
		)
		by_name = {f["fieldname"]: f for f in schema["fields"]}
		self.assertEqual(by_name["nombre"]["fieldtype"], "Data")
		self.assertEqual(by_name["valor"]["fieldtype"], "Small Text")

	def test_controller_holds_title_and_company(self) -> None:
		doc = _make_doc(title="Default - DE", company="Demo Ecuador")
		self.assertEqual(doc.title, "Default - DE")
		self.assertEqual(doc.company, "Demo Ecuador")
