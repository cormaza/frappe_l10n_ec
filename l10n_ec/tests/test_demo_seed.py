import base64
import unittest
from datetime import date

from l10n_ec.ecuador_localization.demo_seed import (
	DEMO_ADDRESS_TEMPLATE,
	DEMO_COMPANY,
	DEMO_COMPANY_ADDRESS,
	DEMO_COMPANY_CO,
	DEMO_EXTRA_DN,
	DEMO_EXTRA_ITEMS,
	DEMO_EXTRA_PURCHASES,
	DEMO_EXTRA_SALES,
	DEMO_GROUPS,
	DEMO_ITEM,
	DEMO_LOGO_FILENAME,
	DEMO_LOGO_PNG,
	DEMO_MASTERS,
	DEMO_PARTIES,
	DEMO_PAYMENTS,
	DEMO_PURCHASE,
	DEMO_RUSTIC_SUPPLIER,
	DEMO_SALES,
	DEMO_SUPPLIER_AUTH,
	DEMO_TIMEZONE,
	DEMO_TODAY,
	NEGATIVE_PARTY,
	PARTY_TYPES,
	WAREHOUSE_TYPES,
	fiscal_year_data,
	group_key,
	master_key,
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
		self.assertRegex(DEMO_TODAY, r"^\d{4}-\d{2}-\d{2}$")
		self.assertEqual(DEMO_TIMEZONE, "America/Guayaquil")
		self.assertEqual(DEMO_COMPANY["default_currency"], "USD")
		self.assertEqual(DEMO_ADDRESS_TEMPLATE["country"], "Ecuador")
		self.assertTrue(DEMO_COMPANY["website"])
		self.assertTrue(DEMO_COMPANY["phone_no"])
		self.assertTrue(DEMO_COMPANY["email"])
		self.assertEqual(
			fiscal_year_data(date(2026, 10, 21)),
			{
				"doctype": "Fiscal Year",
				"year": "2026",
				"year_start_date": "2026-01-01",
				"year_end_date": "2026-12-31",
			},
		)

	def test_company_address_covers_print_dialog(self) -> None:
		for field in ("address_title", "address_line1", "city", "country"):
			self.assertTrue(DEMO_COMPANY_ADDRESS[field], f"Missing {field}")
		self.assertEqual(DEMO_COMPANY_ADDRESS["country"], "Ecuador")
		self.assertTrue(DEMO_COMPANY_ADDRESS["is_your_company_address"])

	def test_demo_logo_is_a_png(self) -> None:
		self.assertTrue(DEMO_LOGO_FILENAME.endswith(".png"))
		self.assertTrue(base64.b64decode(DEMO_LOGO_PNG).startswith(b"\x89PNG"))

	def test_demo_parties_carry_valid_tax_ids(self) -> None:
		for entry in DEMO_PARTIES:
			doc = entry["party"]
			self.assertTrue(
				validate_identification(doc["sri_identification_type"], doc["tax_id"]),
				f"Invalid demo tax ID for {party_name(entry)}",
			)
			if party_name(entry) != "Demo Foreign Co":
				self.assertEqual(entry["address"]["country"], "Ecuador")

	def test_negative_party_is_actually_invalid(self) -> None:
		self.assertFalse(
			validate_identification(NEGATIVE_PARTY["sri_identification_type"], NEGATIVE_PARTY["tax_id"])
		)

	def test_party_names_resolve(self) -> None:
		names = [party_name(entry) for entry in DEMO_PARTIES]
		self.assertEqual(len(set(names)), len(names))
		self.assertIn("Demo Customer RUC", names)

	def test_demo_customer_has_email(self) -> None:
		ruc = next(e for e in DEMO_PARTIES if party_name(e) == "Demo Customer RUC")
		self.assertIn("@", ruc["party"].get("email_id", ""))

	def test_foreign_party_uses_country_not_territory(self) -> None:
		foreign = next(e for e in DEMO_PARTIES if party_name(e) == "Demo Foreign Co")
		self.assertEqual(foreign["address"]["country"], "Colombia")
		self.assertEqual(foreign["party"]["sri_identification_type"], "08")

	def test_masters_have_name_keys(self) -> None:
		keys = [master_key(entry) for entry in DEMO_MASTERS]
		self.assertEqual(len(set(keys)), len(keys))
		self.assertIn("Nos", keys)
		self.assertIn("Demo Stores - DE", keys)

	def test_item_points_to_chart_accounts(self) -> None:
		self.assertEqual(DEMO_ITEM["income_account_number"], "4101")
		self.assertEqual(DEMO_ITEM["expense_account_number"], "520128")
		self.assertEqual(DEMO_ITEM["warehouse"], "Demo Stores - DE")
		self.assertTrue(DEMO_ITEM["description"])

	def test_payment_amounts_match_invoice_totals(self) -> None:
		def with_vat(lines) -> float:
			return round(sum(line["qty"] * line["rate"] for line in lines) * 1.15, 2)

		purchase_total = with_vat(DEMO_PURCHASE["items"])
		sales_total = with_vat(DEMO_SALES["items"])
		by_side = {spec["against"]: spec["amount"] for spec in DEMO_PAYMENTS}
		self.assertEqual(by_side, {"sales": sales_total, "purchase": purchase_total})
		self.assertEqual((purchase_total, sales_total), (115.0, 86.25))

	def test_demo_lines_carry_vat_templates(self) -> None:
		for items in (DEMO_PURCHASE["items"], DEMO_SALES["items"]):
			for line in items:
				self.assertIn("Ecuador VAT 15%", line["item_tax_template"])

	def test_demo_currency_is_usd(self) -> None:
		self.assertEqual(DEMO_COMPANY["default_currency"], "USD")
		self.assertEqual(DEMO_PURCHASE["currency"], "USD")
		self.assertEqual(DEMO_SALES["currency"], "USD")

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


class TestDemoSeedExtension(UnitTestCase):
	"""Pins for the extended demo catalog (multi-tax, multi-flow coverage)."""

	def test_extra_items_cover_zero_five_and_ice(self) -> None:
		codes = [item["item_code"] for item in DEMO_EXTRA_ITEMS]
		self.assertEqual(codes, ["DEMO-WIDGET-ZERO", "DEMO-CEMENT", "DEMO-ICE-BEER"])
		for item in DEMO_EXTRA_ITEMS:
			self.assertEqual(item["item_group"], "Demo Goods")
			self.assertEqual(item["stock_uom"], "Nos")

	def test_foreign_company_and_rustic_supplier(self) -> None:
		self.assertEqual(DEMO_COMPANY_CO["country"], "Colombia")
		self.assertEqual(DEMO_RUSTIC_SUPPLIER["supplier_type"], "Individual")
		self.assertEqual(DEMO_RUSTIC_SUPPLIER["sri_identification_type"], "05")
		self.assertEqual(DEMO_RUSTIC_SUPPLIER["tax_id"], "1710034065")

	def test_extra_purchases_cover_all_flows(self) -> None:
		bills = [spec.get("bill_no") for spec in DEMO_EXTRA_PURCHASES]
		self.assertIn("001-001-000000011", bills)
		self.assertIn("001-001-000000016", bills)
		self.assertIn(None, bills)
		by_bill = {spec.get("bill_no"): spec for spec in DEMO_EXTRA_PURCHASES}
		self.assertEqual(by_bill["001-001-000000012"]["sri_iva_concepto"], "1")
		self.assertEqual(by_bill["001-001-000000016"]["return_against_bill"], "001-001-000000011")
		liquidations = [spec for spec in DEMO_EXTRA_PURCHASES if spec.get("sri_is_liquidacion")]
		self.assertEqual(len(liquidations), 1)
		self.assertEqual(DEMO_SUPPLIER_AUTH, "1234567890")

	def test_extra_sales_cover_received_cycle(self) -> None:
		conceptos = [(spec.get("sri_ir_concepto"), spec.get("sri_iva_concepto")) for spec in DEMO_EXTRA_SALES]
		self.assertIn(("303", "3"), conceptos)
		self.assertEqual(DEMO_EXTRA_SALES[0]["payment"], 900.0)
		self.assertEqual(DEMO_EXTRA_SALES[0]["sri_received_retencion_number"], "001-001-000000101")

	def test_delivery_note_covers_guia_path(self) -> None:
		self.assertEqual(DEMO_EXTRA_DN["customer"], "Demo Customer RUC")
		self.assertEqual(DEMO_EXTRA_DN["items"][0]["qty"], 2)

	def test_wizard_fixtures_cover_company_creation(self) -> None:
		names = [entry["name"] for entry in WAREHOUSE_TYPES]
		self.assertIn("Transit", names)

	def test_extra_purchases_cover_debit_and_sustento(self) -> None:
		by_bill = {spec.get("bill_no"): spec for spec in DEMO_EXTRA_PURCHASES}
		self.assertTrue(by_bill["001-001-000000017"]["sri_is_supplier_debit_note"])
		self.assertEqual(by_bill["001-001-000000011"]["sri_sustento_code"], "06")
		self.assertEqual(by_bill["001-001-000000014"]["sri_sustento_code"], "02")
		self.assertEqual(by_bill["001-001-000000018"]["supplier"], "Demo Rustic Seller")
		ice = by_bill["001-001-000000015"]
		self.assertEqual(ice["items"][0]["item_tax_template"], "Ecuador ICE 5% - Purchases - DE")
