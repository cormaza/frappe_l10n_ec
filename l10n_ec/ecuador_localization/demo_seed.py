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

DEMO_EXTERIOR_SUPPLIERS = [
	{
		"doctype": "Supplier",
		"supplier_name": "Demo Spain Co",
		"supplier_type": "Company",
		"supplier_group": "Demo Suppliers",
		"country": "Spain",
		"sri_identification_type": "06",
		"tax_id": "ESP123456",
	},
	{
		"doctype": "Supplier",
		"supplier_name": "Demo USA Co",
		"supplier_type": "Company",
		"supplier_group": "Demo Suppliers",
		"country": "United States",
		"sri_identification_type": "06",
		"tax_id": "USA123456",
	},
	{
		"doctype": "Supplier",
		"supplier_name": "Demo Panama Co",
		"supplier_type": "Company",
		"supplier_group": "Demo Suppliers",
		"country": "Panama",
		"sri_identification_type": "06",
		"tax_id": "PAN123456",
	},
]

#: (supplier, bill_no, base) exterior purchases (services, no stock, no VAT).
DEMO_EXTERIOR_PURCHASES = [
	("Demo Spain Co", "990001000000001", 1000.00),
	("Demo USA Co", "990001000000002", 2000.00),
	("Demo Panama Co", "990001000000003", 500.00),
]

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
		"bill_no": "001-001-000000019",
		"sri_sustento_code": "06",
		"supplier": "Demo Supplier RUC",
		"apply_tds": 1,
		"sri_assumed_withholding": 1,
		"items": [
			{
				"item_code": "DEMO-WIDGET",
				"qty": 10,
				"rate": 10.0,
				"warehouse": "Demo Stores - DE",
				"item_tax_template": "Ecuador VAT 15% - Purchases - DE",
			}
		],
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


def _seed_demo_emission_point(company: str) -> str | None:
	"""Create the demo points: 001-001 desk, 001-002 locked POS caja.

	Emission points never survived `demo.sh reset` (the seed never created
	them): without one no voucher can take a sequential. Channel separation
	is seeded too: 001-002 carries `pos_only`, so desk emission can never
	consume the caja stream and vice versa.
	"""
	import frappe

	for estab, pto, pos_only, shop_only in (
		("001", "001", 0, 0),
		("001", "002", 1, 0),
		("001", "004", 0, 1),
	):
		name = f"{estab}-{pto}"
		if frappe.db.exists("SRI Emission Point", name):
			frappe.db.set_value("SRI Emission Point", name, "pos_only", pos_only)
			frappe.db.set_value("SRI Emission Point", name, "shop_only", shop_only)
			continue
		frappe.get_doc(
			{
				"doctype": "SRI Emission Point",
				"company": company,
				"establishment_code": estab,
				"emission_point_code": pto,
				"pos_only": pos_only,
				"shop_only": shop_only,
				"sequences": [
					{"document_type": code, "current_sequence": 100}
					for code in ("01", "04", "05", "06", "07")
				],
			}
		).insert(ignore_permissions=True)
	_seed_demo_pos_profile(company)
	if frappe.db.exists("DocType", "Webshop Settings"):
		frappe.db.set_single_value("Webshop Settings", "company", company)
		frappe.db.set_single_value("Webshop Settings", "sri_emission_point", "001-004")
	return "001-001"


def _stage_demo_retencion(
	company: str,
	voucher_number: str,
	purchase_name: str,
	specs: list,
	subject: dict | None = None,
	regime: str | None = None,
	doc_number: str | None = None,
	sustento: str | None = None,
	auth: str | None = None,
) -> str | None:
	"""Build one Authorized-staged 07 from ``[(concepto, base, rate)]`` specs.

	Demo fiction (like the placeholder supplier auths): real
	``build_retencion_xml`` + XSD validation, but SRI never authorized it
	(the demo key is self-signed). Only Form 103 reads 07 vouchers.
	Idempotent: an existing voucher number is returned untouched.
	"""
	import frappe

	if frappe.db.exists("SRI Electronic Voucher", {"sri_number": voucher_number}):
		return frappe.db.get_value("SRI Electronic Voucher", {"sri_number": voucher_number}, "name")
	purchase = frappe.get_doc("Purchase Invoice", purchase_name)
	posting = purchase.posting_date
	issue = posting.strftime("%d/%m/%Y") if hasattr(posting, "strftime") else str(posting)
	period = posting.strftime("%m/%Y") if hasattr(posting, "strftime") else "10/2026"
	from datetime import datetime as _datetime

	auth_date = (
		_datetime(posting.year, posting.month, posting.day, 12, 0, 0)
		if hasattr(posting, "year")
		else _datetime.today().replace(hour=12, minute=0, second=0, microsecond=0)
	)

	from l10n_ec.sri.access_key import generate_access_key
	from l10n_ec.sri.xml_builder import build_retencion_xml, validate_against_xsd

	ruc = frappe.db.get_value("Company", company, "tax_id") or "1760013210001"
	access_key = generate_access_key(
		document_code_sri="07",
		complete_document_number=voucher_number.replace("-", ""),
		environment="1",
		date_document=posting if hasattr(posting, "strftime") else date.today(),
		ruc=ruc,
		numeric_code="12345678",
	)
	sequential = voucher_number.split("-")[-1]
	subject = subject or {
		"id_type": "04",
		"name": "Demo Supplier RUC",
		"tax_id": "1710034065001",
	}

	def _doc(
		concepto: str,
		base: float,
		rate: float,
		doc_number: str = "001-001-000000011",
		sustento: str = "06",
		auth: str = DEMO_SUPPLIER_AUTH,
	) -> dict:
		value = round(base * rate / 100, 2)
		total = round(base * 1.15, 2)
		return {
			"sustento_code": sustento,
			"doc_code": "01",
			"doc_number": doc_number,
			"issue_date": issue,
			"auth_number": auth,
			"local_payment": "01",
			"subtotal": base,
			"total": total,
			"doc_taxes": [
				{
					"tax_code": "2",
					"rate_code": "4",
					"base": base,
					"rate": 15.0,
					"tax_value": round(base * 0.15, 2),
				}
			],
			"withholdings": [
				{"code": "1", "withholding_code": concepto, "base": base, "rate": rate, "value": value}
			],
			"payments": [{"method": "01", "amount": total}],
		}

	xml = build_retencion_xml(
		{
			"environment": "1",
			"doc_code": "07",
			"ruc": ruc,
			"legal_name": company,
			"head_office_address": "Quito",
			"establishment": "001",
			"emission_point": "001",
			"sequential": sequential,
			"access_key": access_key,
			"branch_address": "Quito",
			"special_taxpayer": "",
			"accounting_required": True,
		},
		{
			"issue_date": issue,
			"subject_id_type": subject["id_type"],
			"related_party": "NO",
			"subject_name": subject["name"],
			"subject_id": subject["tax_id"],
			"fiscal_period": period,
			"docs": [
				_doc(
					concepto,
					base,
					rate,
					doc_number=doc_number or "001-001-000000011",
					sustento=sustento or "06",
					auth=auth or DEMO_SUPPLIER_AUTH,
				)
				for concepto, base, rate in specs
			],
		},
	)
	if not validate_against_xsd(xml, "retencion"):
		return None
	voucher = frappe.get_doc(
		{
			"doctype": "SRI Electronic Voucher",
			"access_key": access_key,
			"sri_number": voucher_number,
			"voucher_state": "Authorized",
			"sri_doc_code": "07",
			"company": company,
			"sri_exterior_regime": regime or "",
			"reference_doctype": "Purchase Invoice",
			"reference_name": purchase_name,
			"authorization_number": access_key,
			"authorization_date": auth_date,
			"unsigned_xml": xml,
		}
	)
	voucher.insert(ignore_permissions=True)
	from l10n_ec.ecuador_localization.voucher_flow import persist_voucher_xml

	persist_voucher_xml(voucher, "unsigned_xml")
	voucher.save(ignore_permissions=True)
	return voucher.name


def _seed_demo_withholding_voucher(company: str) -> list:
	"""Stage the demo 07 set so Form 103 shows a spread of casilleros.

	031 keeps its history (312 IR 2% on 100.00); 032 adds 303 honorarios
	10% on 1000.00 + 307 mano de obra 3% on 500.00; 033 adds 340 3% on
	2000.00 (casilleros 3400/3900) + 332 no-sujeto base-only on 500.00.
	"""
	import frappe

	purchase_name = frappe.db.get_value(
		"Purchase Invoice", {"bill_no": "001-001-000000011", "docstatus": 1}, "name"
	)
	if not purchase_name:
		return None
	names = [
		_stage_demo_retencion(company, "001-001-000000031", purchase_name, [("312", 100.00, 2.0)]),
		_stage_demo_retencion(
			company, "001-001-000000032", purchase_name, [("303", 1000.00, 10.0), ("307", 500.00, 3.0)]
		),
		_stage_demo_retencion(
			company, "001-001-000000033", purchase_name, [("340", 2000.00, 3.0), ("332", 500.00, 0.0)]
		),
	]
	return [name for name in names if name]


def _stage_demo_factura_xml(company: str, sales_name: str | None) -> str | None:
	"""Leave one Generated factura with real XML so the 01 RIDE shows emitted truth.

	No SRI round-trip happens here (Generated = honestly EN TRÁMITE): the
	XML is built by the real ``_assemble_payload`` + XSD path and attached
	as a File. Idempotent: an existing 01 voucher for the invoice wins.
	"""
	import frappe

	if not sales_name or not frappe.db.exists("Sales Invoice", sales_name):
		return None
	existing = frappe.db.get_value(
		"SRI Electronic Voucher",
		{"reference_doctype": "Sales Invoice", "reference_name": sales_name, "sri_doc_code": "01"},
		"name",
	)
	if existing:
		return existing
	from l10n_ec.ecuador_localization.voucher_flow import (
		_assemble_payload,
		_resolve_emission_point,
		generate_voucher_xml_doc,
		persist_voucher_xml,
		save_voucher,
	)
	from l10n_ec.sri.access_key import generate_access_key

	si = frappe.get_doc("Sales Invoice", sales_name)
	emission, sequential = _resolve_emission_point(company, "01", "001-001")
	number15 = f"{emission.establishment_code}{emission.emission_point_code}{sequential}"
	issue = si.posting_date
	access_key = generate_access_key(
		document_code_sri="01",
		complete_document_number=number15,
		environment="1",
		date_document=issue if hasattr(issue, "strftime") else date.today(),
		ruc=frappe.db.get_value("Company", company, "tax_id") or "1760013210001",
		numeric_code="12345678",
	)
	voucher = frappe.get_doc(
		{
			"doctype": "SRI Electronic Voucher",
			"access_key": access_key,
			"sri_number": f"{emission.establishment_code}-{emission.emission_point_code}-{sequential}",
			"voucher_state": "Generated",
			"sri_doc_code": "01",
			"company": company,
			"reference_doctype": "Sales Invoice",
			"reference_name": sales_name,
			"unsigned_xml": "",
		}
	)
	voucher.insert(ignore_permissions=True)
	payload = _assemble_payload(voucher)
	generated = generate_voucher_xml_doc(voucher, payload)
	if not generated["ok"]:
		frappe.delete_doc("SRI Electronic Voucher", voucher.name, ignore_permissions=True, force=True)
		return None
	persist_voucher_xml(voucher, "unsigned_xml")
	save_voucher(voucher)
	return voucher.name


def _seed_demo_exterior(company: str, company_address: str) -> list:
	"""Seed exterior suppliers, purchases and staged 07s (ES/US/PA).

	Rates are sourced, never invented (see ``l10n_ec.sri.treaties``):
	Spain regalías 501A 10% con convenio (CDI BOE art. 12.2), USA servicios
	501 25% sin convenio (NAC-DGERCGC26-00000009 art. 4), Panama regalías
	501A 37% paraíso (LRTI art. 39 + NAC-DGERCGC25-00000043). Regime is
	declared per voucher; the collector refuses unsighted pairs.
	"""
	import frappe

	for spec in DEMO_EXTERIOR_SUPPLIERS:
		if not frappe.db.exists("Supplier", spec["supplier_name"]):
			frappe.get_doc(spec).insert(ignore_permissions=True)
	for supplier, bill_no, base in DEMO_EXTERIOR_PURCHASES:
		if frappe.db.exists("Purchase Invoice", {"supplier": supplier, "bill_no": bill_no, "docstatus": 1}):
			continue
		purchase = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": supplier,
				"company": company,
				"billing_address": company_address,
				"currency": "USD",
				"bill_no": bill_no,
				"bill_date": DEMO_TODAY,
				"posting_date": DEMO_TODAY,
				"update_stock": 0,
				"sri_sustento_code": "02",
				"sri_supplier_auth_number": f"99000000{bill_no[-2:]}",
				"items": [{"item_code": "DEMO-WIDGET", "qty": 1, "rate": base}],
			}
		)
		purchase.insert(ignore_permissions=True)
		purchase.submit()
	specs = [
		# (voucher, supplier, bill_no, subject, regime, [(concepto, base, rate)])
		(
			"001-001-000000034",
			"Demo Spain Co",
			"990001000000001",
			{"id_type": "06", "name": "Demo Spain Co", "tax_id": "ESP123456"},
			"con",
			[("501A", 1000.00, 10.0)],
		),
		(
			"001-001-000000035",
			"Demo USA Co",
			"990001000000002",
			{"id_type": "06", "name": "Demo USA Co", "tax_id": "USA123456"},
			"sin",
			[("501", 2000.00, 25.0)],
		),
		(
			"001-001-000000036",
			"Demo Panama Co",
			"990001000000003",
			{"id_type": "06", "name": "Demo Panama Co", "tax_id": "PAN123456"},
			"paraiso",
			[("501A", 500.00, 37.0)],
		),
	]
	names = []
	for voucher_number, supplier, bill_no, subject, regime, rows in specs:
		purchase_name = frappe.db.get_value(
			"Purchase Invoice", {"supplier": supplier, "bill_no": bill_no, "docstatus": 1}, "name"
		)
		if not purchase_name:
			continue
		name = _stage_demo_retencion(
			company,
			voucher_number,
			purchase_name,
			rows,
			subject=subject,
			regime=regime,
			doc_number=bill_no,
			sustento="02",
			auth=f"99000000{bill_no[-2:]}",
		)
		if name:
			names.append(name)
	return names


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
	if frappe.db.get_single_value("Global Defaults", "default_company") != DEMO_COMPANY["company_name"]:
		frappe.db.set_single_value("Global Defaults", "default_company", DEMO_COMPANY["company_name"])
	if frappe.db.get_value("User", "Administrator", "time_zone") != DEMO_TIMEZONE:
		frappe.db.set_value("User", "Administrator", "time_zone", DEMO_TIMEZONE)
	for _company in (DEMO_COMPANY["company_name"], DEMO_COMPANY_CO["company_name"]):
		if frappe.db.exists("Company", _company):
			frappe.db.set_value("Company", _company, "default_currency", "USD")

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
			"sri_assumed_withholding",
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

	report["emission_point"] = _seed_demo_emission_point(company)
	vouchers_07 = _seed_demo_withholding_voucher(company)
	report["withholding_voucher"] = vouchers_07[0] if vouchers_07 else None
	report["withholding_vouchers"] = vouchers_07
	report["exterior_vouchers"] = _seed_demo_exterior(company, company_address)
	report["factura_xml_voucher"] = _stage_demo_factura_xml(company, sales_name)
	report["accounts"] = {
		root: frappe.db.count("Account", {"company": company, "root_type": root})
		for root in ("Asset", "Liability", "Equity", "Income", "Expense")
	}
	report["templates"] = frappe.get_all(
		"Item Tax Template", filters={"company": company}, pluck="title", order_by="title"
	)
	frappe.db.commit()
	return report


def _seed_demo_pos_profile(company: str) -> str | None:
	"""Create the demo caja profile bound to the locked POS point (idempotent)."""
	import frappe

	cash = frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_type": "Cash"}, "name")
	expense = frappe.db.get_value(
		"Account", {"company": company, "root_type": "Expense", "is_group": 0}, "name"
	)
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	if not frappe.db.exists("Mode of Payment", "Cash"):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "Cash", "type": "Cash"}).insert(
			ignore_permissions=True
		)
	mop = frappe.get_doc("Mode of Payment", "Cash")
	if cash and not any(a.default_account == cash for a in mop.accounts):
		mop.append("accounts", {"company": company, "default_account": cash})
		mop.save(ignore_permissions=True)
	if frappe.db.exists("POS Profile", "Demo POS"):
		frappe.db.set_value("POS Profile", "Demo POS", "sri_emission_point", "001-002")
		return "Demo POS"
	frappe.get_doc(
		{
			"doctype": "POS Profile",
			"name": "Demo POS",
			"company": company,
			"warehouse": "Demo Stores - DE",
			"currency": "USD",
			"selling_price_list": "Standard Selling",
			"customer": "Demo Final Consumer",
			"sri_emission_point": "001-002",
			"write_off_account": expense,
			"write_off_cost_center": cost_center,
			"payments": [{"mode_of_payment": "Cash", "default": 1}],
		}
	).insert(ignore_permissions=True)
	return "Demo POS"
