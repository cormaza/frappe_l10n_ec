"""Demo seed for the local demo site (developer tooling, not app runtime).

Run inside bench: `bench --site demo execute
l10n_ec.ecuador_localization.demo_seed.seed_demo`. All builders below are
pure data and pinned by Ring-1 tests; only :func:`seed_demo` touches frappe.
"""

from datetime import date

DEMO_TODAY = date.today().isoformat()
# Site timezone for Ecuador. NOTE: demo.sh reset sets this in its own step
# before seed runs (each bench call is a fresh process reading the new value).
# Evaluating DEMO_TODAY here works because the import happens in that same
# post-timezone process. A manual first seed on a fresh site may still use
# the default timezone; just run seed again.
DEMO_TIMEZONE = "America/Guayaquil"

from l10n_ec.ecuador_localization.chart_setup import (
	INVENTORY_ACCOUNT_NUMBER,
	PAYABLE_ACCOUNT_NUMBER,
	RECEIVABLE_ACCOUNT_NUMBER,
)

DEMO_COMPANY = {
	"abbr": "DE",
	"company_name": "Demo Ecuador",
	"country": "Ecuador",
	"default_currency": "USD",
	"email": "info@demo-ecuador.ec",
	"phone_no": "+593 2 123 4567",
	"tax_id": "1760013210001",
	"website": "https://demo-ecuador.ec",
}

DEMO_COMPANY_ADDRESS = {
	"address_line1": "Av. Amazonas N34-451",
	"address_title": "Demo Ecuador",
	"address_type": "Billing",
	"city": "Quito",
	"country": "Ecuador",
	"is_primary_address": 1,
	"is_your_company_address": 1,
}

# 1x1 transparent PNG placeholder so print formats never ask for a logo.
DEMO_LOGO_FILENAME = "demo-logo.png"
DEMO_LOGO_PNG = (
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

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
			"email_id": "compras@demo-ecuador.ec",
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
	{
		"address": {
			"address_line1": "Calle 100 12-34",
			"address_title": "Demo Foreign Co",
			"address_type": "Billing",
			"city": "Bogota",
			"country": "Colombia",
		},
		"party": {
			"customer_group": "Demo Commercial",
			"customer_name": "Demo Foreign Co",
			"customer_type": "Company",
			"doctype": "Customer",
			"sri_identification_type": "08",
			"tax_id": "ABC-123-EXTERIOR",
			"territory": "Ecuador",
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


def master_key(entry: dict) -> str:
	"""Return the name key of a master-data doc dict."""
	for field in ("uom_name", "item_group_name", "warehouse_name", "price_list_name"):
		if field in entry:
			return entry[field]
	raise KeyError(f"No name key in {entry}")


DEMO_ADDRESS_TEMPLATE = {"doctype": "Address Template", "country": "Ecuador"}

DEMO_MASTERS = [
	{"doctype": "UOM", "uom_name": "Nos"},
	{"doctype": "Item Group", "item_group_name": "All Item Groups", "is_group": 1},
	{
		"doctype": "Item Group",
		"item_group_name": "Demo Goods",
		"is_group": 0,
		"parent_item_group": "All Item Groups",
	},
	{"doctype": "Warehouse", "warehouse_name": "Demo Stores - DE", "company": "Demo Ecuador"},
	{"doctype": "Price List", "price_list_name": "Standard Selling", "currency": "USD", "selling": 1},
	{"doctype": "Price List", "price_list_name": "Standard Buying", "currency": "USD", "buying": 1},
]

DEMO_ITEM = {
	"doctype": "Item",
	"expense_account_number": "520128",
	"income_account_number": "4101",
	"is_stock_item": 1,
	"item_code": "DEMO-WIDGET",
	"item_group": "Demo Goods",
	"item_name": "Demo Widget",
	"description": "Demo widget for electronic invoicing tests",
	"stock_uom": "Nos",
	"warehouse": "Demo Stores - DE",
}

DEMO_EXTRA_ITEMS = [
	{
		"doctype": "Item",
		"expense_account_number": "520128",
		"income_account_number": "4101",
		"is_stock_item": 1,
		"item_code": "DEMO-WIDGET-ZERO",
		"item_group": "Demo Goods",
		"item_name": "Demo Widget Zero",
		"description": "Demo zero-rated product (IVA 0% bucket coverage)",
		"stock_uom": "Nos",
		"warehouse": "Demo Stores - DE",
	},
	{
		"doctype": "Item",
		"expense_account_number": "520128",
		"income_account_number": "4101",
		"is_stock_item": 1,
		"item_code": "DEMO-CEMENT",
		"item_group": "Demo Goods",
		"item_name": "Demo Cement",
		"description": "Demo construction material (IVA 5% bucket coverage)",
		"stock_uom": "Nos",
		"warehouse": "Demo Stores - DE",
	},
	{
		"doctype": "Item",
		"expense_account_number": "520128",
		"income_account_number": "4101",
		"is_stock_item": 1,
		"item_code": "DEMO-ICE-BEER",
		"item_group": "Demo Goods",
		"item_name": "Demo ICE Beer",
		"description": "Demo ICE product (master coverage only; ICE tariffs stay user-configured, no SRI mapping yet)",
		"stock_uom": "Nos",
		"warehouse": "Demo Stores - DE",
	},
	{
		"doctype": "Item",
		"expense_account_number": "520128",
		"income_account_number": "4101",
		"is_stock_item": 1,
		"item_code": "DEMO-TOUR",
		"item_group": "Demo Goods",
		"item_name": "Demo Tour Service",
		"description": "Demo tourism service for holiday 8% IVA scenarios",
		"stock_uom": "Nos",
		"warehouse": "Demo Stores - DE",
	},
]
DEMO_COMPANY_CO = {
	"abbr": "CO",
	"company_name": "Demo Colombia",
	"country": "Colombia",
	"default_currency": "USD",
}

DEMO_RUSTIC_SUPPLIER = {
	"doctype": "Supplier",
	"supplier_name": "Demo Rustic Seller",
	"supplier_type": "Individual",
	"supplier_group": "Demo Suppliers",
	"country": "Ecuador",
	"sri_identification_type": "05",
	"tax_id": "1710034065",
}

DEMO_PURCHASE = {
	"bill_date": DEMO_TODAY,
	"bill_no": "DEMO-BILL-001",
	"currency": "USD",
	"items": [
		{
			"item_code": "DEMO-WIDGET",
			"qty": 10,
			"rate": 10.0,
			"warehouse": "Demo Stores - DE",
			"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
		}
	],
	"supplier": "Demo Supplier RUC",
	"update_stock": 1,
}

DEMO_SALES = {
	"currency": "USD",
	"items": [
		{
			"item_code": "DEMO-WIDGET",
			"qty": 5,
			"rate": 15.0,
			"warehouse": "Demo Stores - DE",
			"item_tax_template": "Ecuador VAT 15% - Sales - DE",
		}
	],
	"party": "Demo Customer RUC",
	"update_stock": 1,
}

DEMO_PAYMENTS = [
	{"amount": 86.25, "against": "sales", "party": "Demo Customer RUC", "payment_type": "Receive"},
	{"amount": 115.0, "against": "purchase", "party": "Demo Supplier RUC", "payment_type": "Pay"},
]

# Demo placeholder for supplier-side SRI authorizations (their data, not ours).
DEMO_SUPPLIER_AUTH = "1234567890"

DEMO_EXTRA_PURCHASES = [
	{
		"bill_no": "001-001-000000011",
		"sri_sustento_code": "06",
		"supplier": "Demo Supplier RUC",
		"apply_tds": 1,
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 10,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
			}
		],
		"payment": 113.0,
	},
	{
		"bill_no": "001-001-000000012",
		"sri_sustento_code": "06",
		"supplier": "Demo Supplier RUC",
		"apply_tds": 1,
		"sri_iva_concepto": "1",
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 10,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
			}
		],
		"payment": 108.50,
	},
	{
		"bill_no": "001-001-000000013",
		"sri_sustento_code": "06",
		"supplier": "Demo Supplier RUC",
		"items": [
			{
				"item_code": "DEMO-WIDGET-ZERO",
				"qty": 10,
				"rate": 5.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 0% - Purchases - DE",
			}
		],
	},
	{
		"bill_no": "001-001-000000014",
		"sri_sustento_code": "02",
		"supplier": "Demo Supplier RUC",
		"items": [
			{
				"item_code": "DEMO-CEMENT",
				"qty": 10,
				"rate": 20.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 5% - Purchases - DE",
			}
		],
	},
	{
		"bill_no": "001-001-000000018",
		"supplier": "Demo Rustic Seller",
		"sri_sustento_code": "06",
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 4,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
			}
		],
	},
	{
		"bill_no": "001-001-000000015",
		"sri_sustento_code": "06",
		"supplier": "Demo Supplier RUC",
		"items": [
			{
				"item_code": "DEMO-ICE-BEER",
				"qty": 10,
				"rate": 5.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador ICE 5% - Purchases - DE",
			}
		],
	},
	{
		"bill_no": "001-001-000000016",
		"sri_sustento_code": "06",
		"supplier": "Demo Supplier RUC",
		"is_return": 1,
		"return_against_bill": "001-001-000000011",
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": -2,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
			}
		],
	},
	{
		"bill_no": "001-001-000000017",
		"supplier": "Demo Supplier RUC",
		"sri_is_supplier_debit_note": 1,
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 1,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
			}
		],
	},
	{
		"bill_no": None,
		"supplier": "Demo Rustic Seller",
		"sri_is_liquidacion": 1,
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 5,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 0% - Purchases - DE",
			}
		],
	},
]

DEMO_EXTRA_SALES = [
	{
		"customer": "Demo Customer RUC",
		"sri_ir_concepto": "303",
		"sri_iva_concepto": "3",
		"sri_received_retencion_number": "001-001-000000101",
		"sri_received_retencion_auth": "2110202607112345678901234567890123456789012",
		"sri_received_retencion_date": DEMO_TODAY,
		"sri_received_retencion_key": "2110202607112345678901234567890123456789012",
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 10,
				"rate": 100.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Sales - DE",
			},
		],
		"payment": 900.0,
	},
	{
		"customer": "Demo Customer RUC",
		"items": [
			{
				"item_code": "DEMO-WIDGET-ZERO",
				"qty": 4,
				"rate": 5.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 0% - Sales - DE",
			}
		],
	},
	{
		"customer": "Demo Customer RUC",
		"items": [
			{
				"item_code": "DEMO-CEMENT",
				"qty": 4,
				"rate": 20.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 5% - Sales - DE",
			},
		],
	},
	{
		"customer": "Demo Customer RUC",
		"tourism_8pct": True,
		"update_stock": 0,
		"items": [
			{
				"item_code": "DEMO-TOUR",
				"qty": 2,
				"rate": 100.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 8% - Sales - DE",
			},
		],
	},
	{
		"customer": "Demo Customer RUC",
		"is_return": 1,
		"return_against_customer": "Demo Customer RUC",
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": -1,
				"rate": 15.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Sales - DE",
			},
		],
	},
]

DEMO_EXTRA_DN = {
	"customer": "Demo Customer RUC",
	"items": [{"item_code": "DEMO-WIDGET", "qty": 2, "rate": 15.0, "warehouse": "Demo Stores - DE"}],
}

# Mirrors ERPNext setup-wizard presets: sites that skip the wizard lack these.
PARTY_TYPES = [
	{"doctype": "Party Type", "party_type": "Customer", "account_type": "Receivable"},
	{"doctype": "Party Type", "party_type": "Supplier", "account_type": "Payable"},
	{"doctype": "Party Type", "party_type": "Employee", "account_type": "Payable"},
	{"doctype": "Party Type", "party_type": "Shareholder", "account_type": "Payable"},
]

# Company creation auto-builds a transit warehouse; the wizard owns this type.
WAREHOUSE_TYPES = [
	{"doctype": "Warehouse Type", "name": "Transit", "warehouse_type": "Transit"},
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

	if frappe.db.get_single_value("System Settings", "time_zone") != DEMO_TIMEZONE:
		frappe.db.set_single_value("System Settings", "time_zone", DEMO_TIMEZONE)

	if not frappe.db.exists("Address Template", {"country": "Ecuador"}):
		frappe.get_doc(DEMO_ADDRESS_TEMPLATE).insert(ignore_permissions=True)

	fiscal_year = fiscal_year_data()
	if not frappe.db.exists("Fiscal Year", fiscal_year["year"]):
		frappe.get_doc(fiscal_year).insert(ignore_permissions=True)

	for party_type in PARTY_TYPES:
		if not frappe.db.exists("Party Type", party_type["party_type"]):
			frappe.get_doc(party_type).insert(ignore_permissions=True)

	for warehouse_type in WAREHOUSE_TYPES:
		if not frappe.db.exists("Warehouse Type", warehouse_type["name"]):
			frappe.get_doc(warehouse_type).insert(ignore_permissions=True)

	if frappe.db.get_single_value("Global Defaults", "default_currency") != "USD":
		frappe.db.set_single_value("Global Defaults", "default_currency", "USD")

	for group in DEMO_GROUPS:
		if not frappe.db.exists(group["doctype"], group_key(group)):
			frappe.get_doc(group).insert(ignore_permissions=True)

	company = DEMO_COMPANY["company_name"]
	if not frappe.db.exists("Company", company):
		frappe.get_doc({"doctype": "Company", **DEMO_COMPANY}).insert(ignore_permissions=True)
	for field in ("website", "phone_no", "email"):
		if not frappe.db.get_value("Company", company, field):
			frappe.db.set_value("Company", company, field, DEMO_COMPANY[field])
	if not frappe.db.exists("File", {"file_name": DEMO_LOGO_FILENAME}):
		import base64

		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": DEMO_LOGO_FILENAME,
				"content": base64.b64decode(DEMO_LOGO_PNG),
				"is_private": 0,
			}
		).insert(ignore_permissions=True)
	logo_url = frappe.db.get_value("File", {"file_name": DEMO_LOGO_FILENAME}, "file_url")
	if logo_url and not frappe.db.get_value("Company", company, "company_logo"):
		frappe.db.set_value("Company", company, "company_logo", logo_url)
	report["company"] = company

	company_address = get_default_address("Company", company)
	if not company_address:
		address = dict(DEMO_COMPANY_ADDRESS)
		address["links"] = [{"link_doctype": "Company", "link_name": company}]
		company_address = (
			frappe.get_doc({"doctype": "Address", **address}).insert(ignore_permissions=True).name
		)
	report["company_address"] = company_address

	for entry in DEMO_PARTIES:
		name = party_name(entry)
		if not frappe.db.exists(entry["party"]["doctype"], name):
			frappe.get_doc(entry["party"]).insert(ignore_permissions=True)
		if not get_default_address(entry["party"]["doctype"], name):
			address = dict(entry["address"])
			address["links"] = [{"link_doctype": entry["party"]["doctype"], "link_name": name}]
			frappe.get_doc({"doctype": "Address", **address}).insert(ignore_permissions=True)
		report["parties"].append(name)

	def account_name(number: str) -> str:
		return frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")

	for entry in DEMO_MASTERS:
		if not frappe.db.exists(entry["doctype"], master_key(entry)):
			doc = dict(entry)
			if doc["doctype"] == "Warehouse":
				doc["account"] = account_name(INVENTORY_ACCOUNT_NUMBER)
			frappe.get_doc(doc).insert(ignore_permissions=True)

	warehouse = frappe.get_doc("Warehouse", "Demo Stores - DE")
	if not warehouse.account:
		warehouse.account = account_name(INVENTORY_ACCOUNT_NUMBER)
		warehouse.save(ignore_permissions=True)

	if not frappe.db.exists("Item", DEMO_ITEM["item_code"]):
		item = dict(DEMO_ITEM)
		item["item_defaults"] = [
			{
				"company": company,
				"default_warehouse": item.pop("warehouse"),
				"income_account": account_name(item.pop("income_account_number")),
				"expense_account": account_name(item.pop("expense_account_number")),
			}
		]
		frappe.get_doc(item).insert(ignore_permissions=True)

	for extra in DEMO_EXTRA_ITEMS:
		if not frappe.db.exists("Item", extra["item_code"]):
			item = dict(extra)
			item["item_defaults"] = [
				{
					"company": company,
					"default_warehouse": item.pop("warehouse"),
					"income_account": account_name(item.pop("income_account_number")),
					"expense_account": account_name(item.pop("expense_account_number")),
				}
			]
			frappe.get_doc(item).insert(ignore_permissions=True)

	if not frappe.db.exists("Company", DEMO_COMPANY_CO["company_name"]):
		frappe.get_doc({"doctype": "Company", **DEMO_COMPANY_CO}).insert(ignore_permissions=True)

	if not frappe.db.exists("Supplier", DEMO_RUSTIC_SUPPLIER["supplier_name"]):
		frappe.get_doc(DEMO_RUSTIC_SUPPLIER).insert(ignore_permissions=True)

	if not frappe.db.get_value("Supplier", "Demo Supplier RUC", "tax_withholding_category"):
		frappe.db.set_value("Supplier", "Demo Supplier RUC", "tax_withholding_category", "Ecuador IR 2%")

	from l10n_ec.ecuador_localization.withholding_setup import setup_ecuadorian_withholdings

	setup_ecuadorian_withholdings(company)

	purchase_name = frappe.db.exists(
		"Purchase Invoice",
		{"supplier": DEMO_PURCHASE["supplier"], "bill_no": DEMO_PURCHASE["bill_no"], "docstatus": 1},
	)
	if not purchase_name:
		purchase = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": DEMO_PURCHASE["supplier"],
				"company": company,
				"billing_address": company_address,
				"currency": DEMO_PURCHASE["currency"],
				"bill_no": DEMO_PURCHASE["bill_no"],
				"bill_date": DEMO_PURCHASE["bill_date"],
				"posting_date": DEMO_PURCHASE["bill_date"],
				"update_stock": 1,
				"items": DEMO_PURCHASE["items"],
			}
		)
		purchase.insert(ignore_permissions=True)
		purchase.submit()
		purchase_name = purchase.name

	sales_name = frappe.db.exists("Sales Invoice", {"customer": DEMO_SALES["party"], "docstatus": 1})
	if not sales_name:
		sales = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": DEMO_SALES["party"],
				"company": company,
				"company_address": company_address,
				"currency": DEMO_SALES["currency"],
				"posting_date": DEMO_PURCHASE["bill_date"],
				"update_stock": 1,
				"items": DEMO_SALES["items"],
			}
		)
		sales.insert(ignore_permissions=True)
		sales.submit()
		sales_name = sales.name

	for spec in DEMO_EXTRA_PURCHASES:
		filters: dict = {"supplier": spec["supplier"], "docstatus": 1}
		if spec.get("bill_no"):
			filters["bill_no"] = spec["bill_no"]
		else:
			filters["sri_is_liquidacion"] = 1
		if frappe.db.exists("Purchase Invoice", filters):
			continue
		doc = {
			"doctype": "Purchase Invoice",
			"supplier": spec["supplier"],
			"company": company,
			"billing_address": company_address,
			"currency": "USD",
			"bill_date": DEMO_TODAY,
			"posting_date": DEMO_TODAY,
			"update_stock": 1,
			"items": spec["items"],
		}
		for key in (
			"bill_no",
			"apply_tds",
			"sri_iva_concepto",
			"sri_is_liquidacion",
			"sri_is_supplier_debit_note",
			"sri_sustento_code",
		):
			if spec.get(key) is not None:
				doc[key] = spec[key]
		if spec.get("bill_no"):
			doc["sri_supplier_auth_number"] = DEMO_SUPPLIER_AUTH
		if spec.get("is_return"):
			target = frappe.db.get_value(
				"Purchase Invoice", {"bill_no": spec["return_against_bill"], "docstatus": 1}, "name"
			)
			if not target:
				continue
			doc["is_return"] = 1
			doc["return_against"] = target
		purchase = frappe.get_doc(doc)
		purchase.insert(ignore_permissions=True)
		purchase.submit()

	for spec in DEMO_EXTRA_SALES:
		if spec.get("is_return"):
			if frappe.db.exists(
				"Sales Invoice", {"customer": spec["customer"], "is_return": 1, "docstatus": 1}
			):
				continue
			doc = {
				"doctype": "Sales Invoice",
				"customer": spec["customer"],
				"company": company,
				"company_address": company_address,
				"currency": "USD",
				"posting_date": DEMO_TODAY,
				"update_stock": 1,
				"is_return": 1,
				"return_against": sales_name,
				"items": spec["items"],
			}
		else:
			if frappe.db.exists(
				"Sales Invoice",
				{
					"customer": spec["customer"],
					"sri_ir_concepto": spec.get("sri_ir_concepto") or "",
					"docstatus": 1,
				},
			):
				continue
			doc = {
				"doctype": "Sales Invoice",
				"customer": spec["customer"],
				"company": company,
				"company_address": company_address,
				"currency": "USD",
				"posting_date": DEMO_TODAY,
				"update_stock": spec.get("update_stock", 1),
				"items": spec["items"],
			}
			for key in (
				"sri_ir_concepto",
				"sri_iva_concepto",
				"sri_received_retencion_number",
				"sri_received_retencion_auth",
				"sri_received_retencion_date",
				"sri_received_retencion_key",
			):
				if spec.get(key) is not None:
					doc[key] = spec[key]
		sale = frappe.get_doc(doc)
		sale.insert(ignore_permissions=True)
		sale.submit()

	if not frappe.db.exists("Delivery Note", {"customer": DEMO_EXTRA_DN["customer"], "docstatus": 1}):
		shipping = get_default_address("Customer", DEMO_EXTRA_DN["customer"])
		delivery = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"customer": DEMO_EXTRA_DN["customer"],
				"company": company,
				"currency": "USD",
				"posting_date": DEMO_TODAY,
				"shipping_address_name": shipping,
				"items": DEMO_EXTRA_DN["items"],
			}
		)
		delivery.insert(ignore_permissions=True)
		delivery.submit()

	cash = account_name("1010101")
	receivable = account_name(RECEIVABLE_ACCOUNT_NUMBER)
	payable = account_name(PAYABLE_ACCOUNT_NUMBER)
	payment_names = []
	for spec in DEMO_PAYMENTS:
		invoice_name = sales_name if spec["against"] == "sales" else purchase_name
		invoice_doctype = "Sales Invoice" if spec["against"] == "sales" else "Purchase Invoice"
		party_type = "Customer" if spec["payment_type"] == "Receive" else "Supplier"
		paid_from = receivable if spec["payment_type"] == "Receive" else cash
		paid_to = cash if spec["payment_type"] == "Receive" else payable
		existing = frappe.db.exists(
			"Payment Entry",
			{"party": spec["party"], "payment_type": spec["payment_type"], "docstatus": 1},
		)
		if existing:
			payment_names.append(existing)
			continue
		payment = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"naming_series": "ACC-PAY-.YYYY.-",
				"payment_type": spec["payment_type"],
				"party_type": party_type,
				"party": spec["party"],
				"company": company,
				"posting_date": DEMO_PURCHASE["bill_date"],
				"paid_amount": spec["amount"],
				"received_amount": spec["amount"],
				"paid_from": paid_from,
				"paid_to": paid_to,
				"paid_from_account_currency": "USD",
				"paid_to_account_currency": "USD",
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"base_paid_amount": spec["amount"],
				"base_received_amount": spec["amount"],
				"references": [
					{
						"reference_doctype": invoice_doctype,
						"reference_name": invoice_name,
						"allocated_amount": spec["amount"],
					}
				],
			}
		)
		payment.insert(ignore_permissions=True)
		payment.submit()
		payment_names.append(payment.name)

	def _pay_invoice(doctype: str, name: str, party_type: str, party: str, amount: float) -> None:
		outstanding = frappe.db.get_value(doctype, name, "outstanding_amount") or 0.0
		if outstanding <= 0:
			return
		amount = min(amount, outstanding)
		if doctype == "Purchase Invoice":
			paid_from, paid_to = cash, payable
			payment_type = "Pay"
		else:
			paid_from, paid_to = receivable, cash
			payment_type = "Receive"
		payment = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"naming_series": "ACC-PAY-.YYYY.-",
				"payment_type": payment_type,
				"party_type": party_type,
				"party": party,
				"company": company,
				"posting_date": DEMO_TODAY,
				"paid_amount": amount,
				"received_amount": amount,
				"paid_from": paid_from,
				"paid_to": paid_to,
				"paid_from_account_currency": "USD",
				"paid_to_account_currency": "USD",
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"base_paid_amount": amount,
				"base_received_amount": amount,
				"references": [
					{
						"reference_doctype": doctype,
						"reference_name": name,
						"allocated_amount": amount,
					}
				],
			}
		)
		payment.insert(ignore_permissions=True)
		payment.submit()
		payment_names.append(payment.name)

	for spec in DEMO_EXTRA_PURCHASES:
		if not spec.get("payment") or not spec.get("bill_no"):
			continue
		name = frappe.db.exists("Purchase Invoice", {"bill_no": spec["bill_no"], "docstatus": 1})
		if name:
			_pay_invoice("Purchase Invoice", name, "Supplier", spec["supplier"], spec["payment"])

	for spec in DEMO_EXTRA_SALES:
		if not spec.get("payment"):
			continue
		name = frappe.db.exists(
			"Sales Invoice",
			{
				"customer": spec["customer"],
				"sri_ir_concepto": spec.get("sri_ir_concepto") or "",
				"docstatus": 1,
			},
		)
		if name:
			_pay_invoice("Sales Invoice", name, "Customer", spec["customer"], spec["payment"])

	report["purchase_invoice"] = purchase_name
	report["sales_invoice"] = sales_name
	report["payments"] = payment_names
	report["stock_on_hand"] = frappe.db.get_value(
		"Bin", {"item_code": "DEMO-WIDGET", "warehouse": "Demo Stores - DE"}, "actual_qty"
	)
	report["outstanding"] = {
		"purchase": frappe.db.get_value("Purchase Invoice", purchase_name, "outstanding_amount"),
		"sales": frappe.db.get_value("Sales Invoice", sales_name, "outstanding_amount"),
	}

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
