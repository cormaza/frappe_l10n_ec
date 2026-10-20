"""Demo seed for the local demo site (developer tooling, not app runtime).

Run inside bench: `bench --site demo execute
l10n_ec.ecuador_localization.demo_seed.seed_demo`. All builders below are
pure data and pinned by Ring-1 tests; only :func:`seed_demo` touches frappe.
"""

from datetime import date

DEMO_COMPANY = {
	"abbr": "DE",
	"company_name": "Demo Ecuador",
	"country": "Ecuador",
	"default_currency": "USD",
	"tax_id": "1760013210001",
}

DEMO_PARTIES = [
	{
		"address": {
			"address_line1": "Av. Amazonas N34-451",
			"address_title": "Demo Customer RUC",
			"address_type": "Billing",
			"city": "Quito",
			"country": "Ecuador",
		},
		"party": {
			"customer_group": "Demo Commercial",
			"customer_name": "Demo Customer RUC",
			"customer_type": "Company",
			"doctype": "Customer",
			"sri_identification_type": "04",
			"tax_id": "1790016919001",
			"territory": "Ecuador",
		},
	},
	{
		"address": {
			"address_line1": "Av. 9 de Octubre 123",
			"address_title": "Demo Final Consumer",
			"address_type": "Billing",
			"city": "Guayaquil",
			"country": "Ecuador",
		},
		"party": {
			"customer_group": "Demo Commercial",
			"customer_name": "Demo Final Consumer",
			"customer_type": "Individual",
			"doctype": "Customer",
			"sri_identification_type": "07",
			"tax_id": "9999999999999",
			"territory": "Ecuador",
		},
	},
	{
		"address": {
			"address_line1": "Calle Larga 4-56",
			"address_title": "Demo Supplier RUC",
			"address_type": "Billing",
			"city": "Cuenca",
			"country": "Ecuador",
		},
		"party": {
			"doctype": "Supplier",
			"sri_identification_type": "04",
			"supplier_group": "Demo Suppliers",
			"supplier_name": "Demo Supplier RUC",
			"supplier_type": "Company",
			"tax_id": "1710034065001",
		},
	},
]

DEMO_GROUPS = [
	{"doctype": "Customer Group", "customer_group_name": "All Customer Groups", "is_group": 1},
	{
		"doctype": "Customer Group",
		"customer_group_name": "Demo Commercial",
		"is_group": 0,
		"parent_customer_group": "All Customer Groups",
	},
	{"doctype": "Territory", "territory_name": "All Territories", "is_group": 1},
	{
		"doctype": "Territory",
		"territory_name": "Ecuador",
		"is_group": 0,
		"parent_territory": "All Territories",
	},
	{"doctype": "Supplier Group", "supplier_group_name": "All Supplier Groups", "is_group": 1},
	{
		"doctype": "Supplier Group",
		"supplier_group_name": "Demo Suppliers",
		"is_group": 0,
		"parent_supplier_group": "All Supplier Groups",
	},
]


def group_key(group: dict) -> str:
	"""Return the name key of a group doc dict."""
	return group.get("customer_group_name") or group.get("territory_name") or group.get("supplier_group_name")


DEMO_ADDRESS_TEMPLATE = {"doctype": "Address Template", "country": "Ecuador"}

# Mirrors ERPNext setup-wizard presets: sites that skip the wizard lack these.
PARTY_TYPES = [
	{"doctype": "Party Type", "party_type": "Customer", "account_type": "Receivable"},
	{"doctype": "Party Type", "party_type": "Supplier", "account_type": "Payable"},
	{"doctype": "Party Type", "party_type": "Employee", "account_type": "Payable"},
	{"doctype": "Party Type", "party_type": "Shareholder", "account_type": "Payable"},
]

NEGATIVE_PARTY = {
	"customer_group": "Demo Commercial",
	"customer_name": "Demo Invalid Tax ID",
	"customer_type": "Company",
	"doctype": "Customer",
	"sri_identification_type": "04",
	"tax_id": "1790016819001",
	"territory": "Ecuador",
}


def fiscal_year_data(today: date | None = None) -> dict:
	"""Build the current-year Fiscal Year doc dict (calendar year)."""
	year = str((today or date.today()).year)
	return {
		"doctype": "Fiscal Year",
		"year": year,
		"year_start_date": f"{year}-01-01",
		"year_end_date": f"{year}-12-31",
	}


def party_name(entry: dict) -> str:
	"""Return the primary name field of a party doc dict."""
	doc = entry["party"] if "party" in entry else entry
	return doc.get("customer_name") or doc.get("supplier_name")


def seed_demo() -> dict:
	"""Create demo company, parties, and addresses; report validation behavior."""
	import frappe
	from frappe.contacts.doctype.address.address import get_default_address

	report: dict = {"company": None, "parties": [], "negative_blocked": False}

	if not frappe.db.exists("Address Template", {"country": "Ecuador"}):
		frappe.get_doc(DEMO_ADDRESS_TEMPLATE).insert(ignore_permissions=True)

	fiscal_year = fiscal_year_data()
	if not frappe.db.exists("Fiscal Year", fiscal_year["year"]):
		frappe.get_doc(fiscal_year).insert(ignore_permissions=True)

	for party_type in PARTY_TYPES:
		if not frappe.db.exists("Party Type", party_type["party_type"]):
			frappe.get_doc(party_type).insert(ignore_permissions=True)

	for group in DEMO_GROUPS:
		if not frappe.db.exists(group["doctype"], group_key(group)):
			frappe.get_doc(group).insert(ignore_permissions=True)

	company = DEMO_COMPANY["company_name"]
	if not frappe.db.exists("Company", company):
		frappe.get_doc({"doctype": "Company", **DEMO_COMPANY}).insert(ignore_permissions=True)
	report["company"] = company

	for entry in DEMO_PARTIES:
		name = party_name(entry)
		if not frappe.db.exists(entry["party"]["doctype"], name):
			frappe.get_doc(entry["party"]).insert(ignore_permissions=True)
		if not get_default_address(entry["party"]["doctype"], name):
			address = dict(entry["address"])
			address["links"] = [{"link_doctype": entry["party"]["doctype"], "link_name": name}]
			frappe.get_doc({"doctype": "Address", **address}).insert(ignore_permissions=True)
		report["parties"].append(name)

	negative_name = NEGATIVE_PARTY["customer_name"]
	negative = frappe.get_doc(dict(NEGATIVE_PARTY)).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Address",
			"address_line1": "Calle Falsa 123",
			"address_title": negative_name,
			"address_type": "Billing",
			"city": "Quito",
			"country": "Ecuador",
			"is_primary_address": 1,
			"links": [{"link_doctype": "Customer", "link_name": negative.name}],
		}
	).insert(ignore_permissions=True)
	try:
		frappe.db.savepoint("demo_negative_case")
		negative.reload()
		negative.save(ignore_permissions=True)
	except Exception:
		report["negative_blocked"] = True
		frappe.db.rollback(save_point="demo_negative_case")
	finally:
		for doctype, title in (("Address", negative_name), ("Customer", negative_name)):
			if frappe.db.exists(doctype, title):
				frappe.delete_doc(doctype, title, ignore_permissions=True, force=True)

	report["accounts"] = {
		root: frappe.db.count("Account", {"company": company, "root_type": root})
		for root in ("Asset", "Liability", "Equity", "Income", "Expense")
	}
	report["templates"] = frappe.get_all(
		"Item Tax Template", filters={"company": company}, pluck="title", order_by="title"
	)
	frappe.db.commit()
	return report
