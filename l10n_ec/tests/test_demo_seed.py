import unittest
from datetime import date

from l10n_ec.ecuador_localization.demo_seed import (
	DEMO_ADDRESS_TEMPLATE,
	DEMO_COMPANY,
	DEMO_GROUPS,
	DEMO_PARTIES,
	NEGATIVE_PARTY,
	PARTY_TYPES,
	fiscal_year_data,
	group_key,
	party_name,
)
from l10n_ec.sri.identification import validate_identification

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestDemoSeed(UnitTestCase):
	"""Unit tests pinning the demo seed data (no database)."""

	def test_demo_company_is_ecuadorian(self) -> None:
		self.assertEqual(DEMO_COMPANY["country"], "Ecuador")
		self.assertEqual(DEMO_COMPANY["default_currency"], "USD")
		self.assertEqual(DEMO_ADDRESS_TEMPLATE["country"], "Ecuador")
		self.assertEqual(
			fiscal_year_data(date(2026, 10, 21)),
			{
				"doctype": "Fiscal Year",
				"year": "2026",
				"year_start_date": "2026-01-01",
				"year_end_date": "2026-12-31",
			},
		)

	def test_demo_parties_carry_valid_tax_ids(self) -> None:
		for entry in DEMO_PARTIES:
			doc = entry["party"]
			self.assertTrue(
				validate_identification(doc["sri_identification_type"], doc["tax_id"]),
				f"Invalid demo tax ID for {party_name(entry)}",
			)
			self.assertEqual(entry["address"]["country"], "Ecuador")

	def test_negative_party_is_actually_invalid(self) -> None:
		self.assertFalse(
			validate_identification(NEGATIVE_PARTY["sri_identification_type"], NEGATIVE_PARTY["tax_id"])
		)

	def test_party_names_resolve(self) -> None:
		names = [party_name(entry) for entry in DEMO_PARTIES]
		self.assertEqual(len(set(names)), len(names))
		self.assertIn("Demo Customer RUC", names)

	def test_party_types_mirror_wizard_presets(self) -> None:
		by_type = {row["party_type"]: row["account_type"] for row in PARTY_TYPES}
		self.assertEqual(
			by_type,
			{
				"Customer": "Receivable",
				"Supplier": "Payable",
				"Employee": "Payable",
				"Shareholder": "Payable",
			},
		)

	def test_party_groups_are_seeded_leaves(self) -> None:
		by_key = {group_key(group): group for group in DEMO_GROUPS}
		for entry in DEMO_PARTIES:
			doc = entry["party"]
			for field in ("customer_group", "territory", "supplier_group"):
				if field in doc:
					group = by_key.get(doc[field])
					self.assertIsNotNone(group, f"Unseeded group {doc[field]}")
					self.assertFalse(group.get("is_group"), f"{doc[field]} must be a leaf")
		for group in DEMO_GROUPS:
			if not group.get("is_group"):
				parent_field = {
					"Customer Group": "parent_customer_group",
					"Territory": "parent_territory",
					"Supplier Group": "parent_supplier_group",
				}[group["doctype"]]
				parent = by_key.get(group.get(parent_field))
				self.assertIsNotNone(parent, f"Missing parent for {group_key(group)}")
				self.assertTrue(parent.get("is_group"))
