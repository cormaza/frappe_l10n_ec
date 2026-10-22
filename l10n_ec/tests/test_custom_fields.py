import unittest

from l10n_ec.ecuador_localization.custom_fields import CUSTOM_FIELDS

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

EXPECTED_FIELDS = {
	"Company": {
		"sri_environment",
		"special_taxpayer_resolution",
		"sri_signature",
		"withholding_agent_resolution",
		"rimpe_regime",
		"accounting_required",
	},
	"Customer": {"sri_identification_type", "sri_related_party"},
	"Mode of Payment": {"sri_payment_code"},
	"Quotation": {"sri_info_adicional", "sri_emission_point"},
	"Sales Order": {"sri_info_adicional", "sri_emission_point"},
	"Webshop Settings": {"sri_emission_point"},
	"Purchase Invoice": {
		"sri_supplier_auth_number",
		"sri_sustento_code",
		"sri_is_liquidacion",
		"sri_is_supplier_debit_note",
		"sri_iva_concepto",
	},
	"Sales Invoice": {
		"sri_info_adicional",
		"sri_ir_concepto",
		"sri_iva_concepto",
		"sri_received_retencion_number",
		"sri_received_retencion_auth",
		"sri_received_retencion_date",
		"sri_received_retencion_key",
	},
	"Supplier": {"sri_identification_type", "sri_related_party"},
	"POS Profile": {"sri_emission_point"},
	"POS Invoice": {"sri_emission_point", "pos_opening_entry"},
}


class TestSRICustomFields(UnitTestCase):
	"""Unit tests pinning the Phase 3 custom field definitions (no database)."""

	def test_expected_fields_per_doctype(self) -> None:
		self.assertEqual(set(CUSTOM_FIELDS), set(EXPECTED_FIELDS))
		for doctype, expected in EXPECTED_FIELDS.items():
			self.assertEqual(
				{f["fieldname"] for f in CUSTOM_FIELDS[doctype]},
				expected,
				f"Custom fields drift on {doctype}",
			)

	def test_field_definitions_are_well_formed(self) -> None:
		for doctype, fields in CUSTOM_FIELDS.items():
			for field in fields:
				self.assertTrue(field["fieldname"], f"Missing fieldname on {doctype}")
				self.assertTrue(field["label"], f"Missing label on {doctype}")
				self.assertTrue(field["fieldtype"], f"Missing fieldtype on {doctype}")
				self.assertTrue(field["insert_after"], f"Missing insert_after on {doctype}")
				if field["fieldtype"] == "Select":
					self.assertIn("options", field, f"Select without options on {doctype}")
				if field["fieldtype"] == "Link":
					self.assertTrue(field.get("options"), f"Link without target DocType on {doctype}")

	def test_identification_link_points_to_catalog(self) -> None:
		for doctype in ("Customer", "Supplier"):
			link = next(f for f in CUSTOM_FIELDS[doctype] if f["fieldname"] == "sri_identification_type")
			self.assertEqual(link["options"], "SRI Identification Type")

	def test_company_fields_hide_outside_ecuador(self) -> None:
		for field in CUSTOM_FIELDS["Company"]:
			self.assertEqual(
				field.get("depends_on"),
				"eval:doc.country=='Ecuador'",
				f"Missing gate on {field['fieldname']}",
			)
		for doctype in ("Customer", "Supplier"):
			for field in CUSTOM_FIELDS[doctype]:
				self.assertNotIn("depends_on", field)
