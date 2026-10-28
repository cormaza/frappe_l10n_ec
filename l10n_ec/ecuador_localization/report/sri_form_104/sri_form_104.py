"""Thin Frappe Script Report: SRI Form 104 (IVA casilleros).

Bench executes :func:`execute` over the posted month ledger of the filtered
company/month (submitted Sales/Purchase Invoices, IVA deduction rows, and
received-withholding settlement Journal Entries); the pure collector
(``l10n_ec/sri/form104.py``) owns every mapping rule. Fixed-asset, import,
export, variable-rate, and prior-period boxes stay zero: the ledger carries
no input that distinguishes them. Customer-issued retencion slips have no
stored doctype, so ``received_refs`` arrives empty from the bench fetch and
travels with the ledger argument when supplied. Ring-1 importable via the
``frappe`` import guard (no database, empty data).
"""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.form104 import FORM104_BOXES, collect_104
from l10n_ec.sri.form104_layout import build_104_rows


def execute(filters=None):
	"""Run the SRI Form 104 Script Report; DIMM-style blocks and labels."""
	columns = [
		{"fieldname": "descripcion", "label": _("Description"), "fieldtype": "Data", "width": 570},
		{"fieldname": "casilleros", "label": _("Boxes"), "fieldtype": "Data", "width": 125},
		{"fieldname": "signo", "label": _("Sign"), "fieldtype": "Data", "width": 45},
		{"fieldname": "bruto", "label": _("Gross value"), "fieldtype": "Float", "width": 100},
		{"fieldname": "neto", "label": _("Net value"), "fieldtype": "Float", "width": 100},
		{"fieldname": "impuesto", "label": _("Tax"), "fieldtype": "Float", "width": 90},
	]
	if frappe is None:  # Ring 1: importable, no database.
		return columns, []
	year = int(filters.get("year") or 0) if filters else 0
	month = int(filters.get("month") or 0) if filters else 0
	company = filters.get("company") if filters else None
	if not company or not year or not month:
		return columns, []
	totals = collect_104(_fetch_month_ledger(company, year, month), year, month)
	data = build_104_rows({box: value for box, value in totals.items() if box in FORM104_BOXES})
	summary = [
		{"label": _("Total consolidated (859)"), "value": totals.get("859", 0.0), "indicator": "blue"},
		{"label": _("Payable (perception 699)"), "value": totals.get("699", 0.0), "indicator": "orange"},
		{"label": _("Withheld (retention 801)"), "value": totals.get("801", 0.0), "indicator": "green"},
		{"label": _("Credit (602)"), "value": totals.get("602", 0.0), "indicator": "grey"},
	]
	return columns, data, None, None, summary, True


def _fetch_month_ledger(company: str, year: int, month: int) -> dict:
	"""Posted month ledger shaped for :func:`collect_104`."""
	import calendar

	from l10n_ec.ecuador_localization.received_settlement import (
		IR_CREDIT_ACCOUNT_NUMBER,
		IVA_CREDIT_ACCOUNT_NUMBER,
	)
	from l10n_ec.ecuador_localization.validation import IVA_WH_ACCOUNT_NUMBER
	from l10n_ec.sri.tax_codes import tax_codes_for_template

	last_day = calendar.monthrange(year, month)[1]
	start = f"{year}-{month:02d}-01"
	end = f"{year}-{month:02d}-{last_day:02d}"
	rate_cache: dict = {}

	def _template_rate(template: str) -> float:
		if template not in rate_cache:
			doc = frappe.get_doc("Item Tax Template", template)
			rate_cache[template] = doc.taxes[0].tax_rate if doc.taxes else 0.0
		return rate_cache[template]

	def _invoice_taxes(doctype: str) -> list:
		rows = []
		names = frappe.get_all(
			doctype,
			filters={"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]},
			pluck="name",
		)
		for name in names:
			doc = frappe.get_doc(doctype, name)
			is_return = bool(doc.get("is_return"))
			settlement_linked = doctype == "Purchase Invoice" and bool(
				frappe.db.exists("SRI Import Settlement", {"purchase_invoice": name})
			)
			for item in doc.items:
				template = item.get("item_tax_template")
				if not template:
					continue
				code, rate_code = tax_codes_for_template(template)
				base = item.get("net_amount") or item.get("amount") or 0.0
				tarifa = _template_rate(template)
				rows.append(
					{
						"code": code,
						"rate_code": rate_code,
						"tarifa": tarifa,
						"base": base,
						"value": round(base * tarifa / 100, 2),
						"is_return": is_return,
						"import_kind": _import_kind(item) if settlement_linked else None,
					}
				)
		return rows

	def _import_kind(item) -> str:
		"""Classify a settlement-linked item into its DIMM import triple."""
		flags = frappe.db.get_value("Item", item.get("item_code"), ["is_stock_item", "is_fixed_asset"])
		is_stock, is_fixed = flags or (None, None)
		if is_fixed:
			return "fixed_asset"
		if not is_stock:
			return "services"
		return "goods"

	deduction_account = frappe.db.get_value(
		"Account", {"company": company, "account_number": IVA_WH_ACCOUNT_NUMBER}, "name"
	)
	deduction_rows = []
	if deduction_account:
		for name in frappe.get_all(
			"Purchase Invoice",
			filters={"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]},
			pluck="name",
		):
			doc = frappe.get_doc("Purchase Invoice", name)
			for row in doc.taxes:
				if row.get("add_deduct_tax") != "Deduct" or row.get("account_head") != deduction_account:
					continue
				deduction_rows.append(
					{"rate": row.get("rate") or 0.0, "amount": abs(row.get("tax_amount") or 0.0)}
				)

	asset_numbers = {}
	for number in (IVA_CREDIT_ACCOUNT_NUMBER, IR_CREDIT_ACCOUNT_NUMBER):
		account = frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")
		if account:
			asset_numbers[account] = number
	settlements = []
	if asset_numbers:
		for name in frappe.get_all(
			"Journal Entry",
			filters={"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]},
			pluck="name",
		):
			doc = frappe.get_doc("Journal Entry", name)
			for row in doc.accounts:
				if row.get("account") in asset_numbers:
					settlements.append(
						{
							"account_number": asset_numbers[row.get("account")],
							"debit": row.get("debit_in_account_currency") or 0.0,
						}
					)

	return {
		"sales_taxes": _invoice_taxes("Sales Invoice"),
		"purchase_taxes": _invoice_taxes("Purchase Invoice"),
		"iva_deduction_rows": deduction_rows,
		"settlements": settlements,
		"received_refs": _received_refs(company, start, end),
	}


def _received_refs(company: str, start: str, end: str) -> list:
	"""Customer-issued retencion references from submitted sales invoices."""
	refs = []
	for name in frappe.get_all(
		"Sales Invoice",
		filters={"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]},
		pluck="name",
	):
		doc = frappe.get_doc("Sales Invoice", name)
		if not doc.get("sri_received_retencion_number"):
			continue
		values = _settlement_values(name)
		refs.append(
			{
				"number": doc.get("sri_received_retencion_number"),
				"authorization": doc.get("sri_received_retencion_auth") or "",
				"date": str(doc.get("sri_received_retencion_date") or ""),
				"iva_value": (values or {}).get("iva_value", 0.0),
				"renta_value": (values or {}).get("renta_value", 0.0),
			}
		)
	return refs


def _settlement_values(sales_invoice: str) -> dict | None:
	"""Received-withholding values from the settlement JE, if posted."""
	from l10n_ec.ecuador_localization.received_settlement import settlement_values

	return settlement_values(sales_invoice)
