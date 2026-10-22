"""Bench-side ATS month reader: posted documents to collector input shapes.

The collector (`ats_collector`) aggregates plain dicts; this module fetches
posted Purchase/Sales Invoices on a bench site and shapes them. Shaping
helpers are pure (Ring-1 tested); only :func:`read_month` touches frappe.

Fiscal-existence rule: only Authorized emissions feed ATS sections. Supplier
invoices qualify by SRI number + stored supplier auth; our sales qualify by
authorized 01 voucher; unauthorized/unemitted docs are skipped (they do not
exist fiscally), never fabricated. Authorized-then-voided (Annulled) vouchers
feed the cancelled section with their SRI + authorization numbers: they
fiscally existed, unlike never-authorized cancels which stay excluded.
"""

import re

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


SRI_NUMBER_PATTERN = re.compile(r"^\d{3}-\d{3}-\d{9}$")


def is_sri_number(value: str | None) -> bool:
	"""Whether a document number is an SRI-formatted `001-001-000000001`."""
	return bool(value and SRI_NUMBER_PATTERN.match(value.strip()))


def classify_purchase(is_return: bool, is_liquidacion: bool, is_debit_note: bool) -> str:
	"""ATS document code for a purchase (fail loud on contradictory states)."""
	if is_return and is_liquidacion:
		raise ValueError(_("A purchase cannot be a return and a liquidacion at once."))
	if is_return:
		return "04"
	if is_debit_note:
		return "05"
	if is_liquidacion:
		return "03"
	return "01"


def purchase_row(pi: dict, supplier: dict, voucher: dict | None, doc_code: str = "01") -> dict:
	"""Shape one submitted Purchase Invoice for the ATS collector."""
	number = pi.get("bill_no", "")
	auth = pi.get("sri_supplier_auth_number", "")
	if doc_code == "03" and voucher is not None:
		number = voucher.get("sri_number", number)
		auth = voucher.get("authorization_number", auth)
	row: dict = {
		"supplier_id_type": supplier.get("sri_identification_type", ""),
		"supplier_id": supplier.get("tax_id", ""),
		"supplier_name": supplier.get("supplier_name", ""),
		"sustento_code": pi.get("sri_sustento_code", "02"),
		"doc_code": doc_code,
		"sri_number": number,
		"issue_date": pi.get("bill_date", ""),
		"register_date": pi.get("posting_date", ""),
		"auth_number": auth,
		"taxes": pi.get("taxes", []),
		"ice_amount": round(sum(t.get("value", 0.0) for t in pi.get("taxes", []) if t.get("code") == "3"), 2),
		"payments": [{"method": "01", "amount": pi.get("grand_total", 0.0)}],
	}
	if voucher is not None and voucher.get("voucher_state") == "Authorized" and voucher.get("body"):
		body = voucher["body"]
		row["withholdings"] = [
			{
				"concepto": withholding.get("withholding_code", ""),
				"base": withholding.get("base", 0.0),
				"rate": withholding.get("rate", 0.0),
				"value": withholding.get("value", 0.0),
			}
			for sustento in body.get("docs", [])
			for withholding in sustento.get("withholdings", [])
		]
		row["retencion"] = {
			"number": voucher.get("sri_number", ""),
			"authorization": voucher.get("authorization_number", ""),
			"date": _iso_to_sri(voucher.get("authorization_date", "")),
		}
	return row


def sale_row(si: dict, customer: dict, voucher: dict | None, settlement: dict | None) -> dict:
	"""Shape one authorized sale for the ATS collector."""
	row: dict = {
		"customer_id_type": customer.get("sri_identification_type", ""),
		"customer_id": customer.get("tax_id", ""),
		"customer_name": customer.get("customer_name", ""),
		"doc_code": "01",
		"sri_number": voucher.get("sri_number", "") if voucher else "",
		"issue_date": si.get("posting_date", ""),
		"auth_number": voucher.get("authorization_number", "") if voucher else "",
		"taxes": si.get("taxes", []),
		"ice_amount": round(sum(t.get("value", 0.0) for t in si.get("taxes", []) if t.get("code") == "3"), 2),
		"payments": [{"method": "01", "amount": si.get("grand_total", 0.0)}],
	}
	if settlement is not None:
		row["received"] = {
			"retencion_number": si.get("sri_received_retencion_number", ""),
			"authorization": si.get("sri_received_retencion_auth", ""),
			"date": si.get("sri_received_retencion_date", ""),
			"access_key": si.get("sri_received_retencion_key", ""),
			"iva_value": settlement.get("iva_value", 0.0),
			"renta_value": settlement.get("renta_value", 0.0),
		}
	return row


def annulled_row(voucher: dict) -> dict:
	"""Shape one Annulled voucher for the ATS cancelled section.

	Matches the `collect_cancelled` input shape: the SRI number plus the
	authorization number prove the doc fiscally existed before its void.
	"""
	return {
		"doc_code": voucher.get("sri_doc_code", ""),
		"sri_number": voucher.get("sri_number", ""),
		"auth_number": voucher.get("authorization_number", ""),
	}


def _annulled_vouchers(company: str, start: str, end: str) -> list:
	"""Annulled vouchers authorized in the month, shaped for `collect_month`."""
	if frappe is None:  # pragma: no cover
		return []
	names = frappe.get_all(
		"SRI Electronic Voucher",
		filters={
			"company": company,
			"voucher_state": "Annulled",
			"authorization_date": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]],
		},
		pluck="name",
	)
	rows = []
	for name in names:
		voucher = frappe.get_doc("SRI Electronic Voucher", name)
		rows.append(
			annulled_row(
				{
					"sri_doc_code": voucher.get("sri_doc_code"),
					"sri_number": voucher.get("sri_number"),
					"authorization_number": voucher.get("authorization_number"),
				}
			)
		)
	return rows


def _authorized_voucher(reference_doctype: str, reference_name: str) -> dict | None:
	"""Latest Authorized voucher data + parsed body for a reference, if any."""
	if frappe is None:  # pragma: no cover
		return None
	from l10n_ec.sri.voucher_data import parse_emitted_xml

	name = frappe.db.get_value(
		"SRI Electronic Voucher",
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"voucher_state": "Authorized",
		},
		"name",
		order_by="modified desc",
	)
	if not name:
		return None
	voucher = frappe.get_doc("SRI Electronic Voucher", name)
	if not voucher.get("unsigned_xml"):
		return None
	file_name = frappe.db.get_value("File", {"file_url": voucher.get("unsigned_xml")}, "name")
	if not file_name:
		return None
	return {
		"body": parse_emitted_xml(frappe.get_doc("File", file_name).get_content()),
		"voucher_state": voucher.get("voucher_state"),
		"sri_number": voucher.get("sri_number"),
		"authorization_number": voucher.get("authorization_number"),
		"authorization_date": voucher.get("authorization_date"),
	}


def _authorized_vouchers(reference_doctype: str, reference_name: str) -> list:
	"""Every Authorized voucher body for a reference, oldest first (bench only)."""
	if frappe is None:  # pragma: no cover
		return []
	from l10n_ec.sri.voucher_data import parse_emitted_xml

	names = frappe.get_all(
		"SRI Electronic Voucher",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"voucher_state": "Authorized",
		},
		pluck="name",
		order_by="creation asc",
	)
	vouchers = []
	for name in names:
		voucher = frappe.get_doc("SRI Electronic Voucher", name)
		if not voucher.get("unsigned_xml"):
			continue
		file_name = frappe.db.get_value("File", {"file_url": voucher.get("unsigned_xml")}, "name")
		if not file_name:
			continue
		vouchers.append(
			{
				"body": parse_emitted_xml(frappe.get_doc("File", file_name).get_content()),
				"voucher_state": voucher.get("voucher_state"),
				"sri_number": voucher.get("sri_number"),
				"authorization_number": voucher.get("authorization_number"),
				"authorization_date": voucher.get("authorization_date"),
			}
		)
	return vouchers


def _settlement_values(sales_invoice: str) -> dict | None:
	"""Received-withholding values from the settlement JE, if posted."""
	from l10n_ec.ecuador_localization.received_settlement import settlement_values

	return settlement_values(sales_invoice)


def _iso_to_sri(value) -> str:
	"""`YYYY-MM-DD` (date, Datetime, or string) to `DD/MM/YYYY`; empty stays empty."""
	text = str(value or "").strip().split(" ")[0]
	parts = text.split("-")
	if len(parts) == 3 and len(parts[0]) == 4:
		return f"{parts[2]}/{parts[1]}/{parts[0]}"
	return text


def _voucher_taxes(voucher: dict, mapped: list) -> list:
	"""Tax rows for one authorized sale: the emitted XML when it carries them.

	A consolidated invoice has no usable tax rows of its own (the merge
	leaves the table empty) while each ticket voucher embeds its own
	`totalConImpuestos`: the XML is the single source of truth. Plain SI
	vouchers fall back to the mapped invoice lines (same numbers).
	"""
	body = (voucher or {}).get("body") or {}
	if body.get("kind") == "factura" and body.get("taxes"):
		return body["taxes"]
	return [tax for line in mapped for tax in line.get("taxes", [])]


def read_month(company: str, year: int, month: int) -> dict:
	"""Fetch posted month documents shaped for :func:`collect_month`."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to read posted documents.")
	from l10n_ec.ecuador_localization.voucher_flow import base_lines, map_line_taxes

	informante = frappe.db.get_value("Company", company, ["tax_id", "company_name"], as_dict=True)

	start = f"{year}-{month:02d}-01"
	end = f"{year}-{month:02d}-31"
	purchases = []
	for name in frappe.get_all(
		"Purchase Invoice",
		filters={"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]},
		pluck="name",
	):
		pi = frappe.get_doc("Purchase Invoice", name)
		doc_code = classify_purchase(
			bool(pi.get("is_return")),
			bool(pi.get("sri_is_liquidacion")),
			bool(pi.get("sri_is_supplier_debit_note")),
		)
		if doc_code == "01" and not is_sri_number(pi.get("bill_no")):
			continue
		supplier = frappe.get_doc("Supplier", pi.get("supplier"))
		mapped = [map_line_taxes(line) for line in base_lines(pi)]
		voucher = _authorized_voucher("Purchase Invoice", name)
		if doc_code == "03" and voucher is None:
			continue
		purchases.append(
			purchase_row(
				{
					"bill_no": pi.get("bill_no"),
					"bill_date": _iso_to_sri(pi.get("bill_date")),
					"posting_date": _iso_to_sri(pi.get("posting_date")),
					"grand_total": pi.get("grand_total"),
					"sri_supplier_auth_number": pi.get("sri_supplier_auth_number") or "",
					"sri_sustento_code": pi.get("sri_sustento_code") or "02",
					"taxes": [
						{
							"code": tax["code"],
							"rate_code": tax["rate_code"],
							"base": tax["base"],
							"value": tax["value"],
						}
						for line in mapped
						for tax in line["taxes"]
					],
				},
				{
					"sri_identification_type": supplier.get("sri_identification_type"),
					"tax_id": supplier.get("tax_id"),
					"supplier_name": supplier.get("supplier_name"),
				},
				voucher,
				doc_code,
			)
		)
	sales = []
	for name in frappe.get_all(
		"Sales Invoice",
		filters={"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]},
		pluck="name",
	):
		vouchers = _authorized_vouchers("Sales Invoice", name)
		if not vouchers:
			continue
		si = frappe.get_doc("Sales Invoice", name)
		customer = frappe.get_doc("Customer", si.get("customer"))
		mapped = [map_line_taxes(line) for line in base_lines(si)]
		for voucher in vouchers:
			sales.append(
				sale_row(
					{
						"posting_date": _iso_to_sri(si.get("posting_date")),
						"grand_total": si.get("grand_total"),
						"taxes": _voucher_taxes(voucher, mapped),
						"sri_received_retencion_number": si.get("sri_received_retencion_number") or "",
						"sri_received_retencion_auth": si.get("sri_received_retencion_auth") or "",
						"sri_received_retencion_date": _iso_to_sri(si.get("sri_received_retencion_date")),
						"sri_received_retencion_key": si.get("sri_received_retencion_key") or "",
					},
					{
						"sri_identification_type": customer.get("sri_identification_type"),
						"tax_id": customer.get("tax_id"),
						"customer_name": customer.get("customer_name"),
					},
					voucher,
					_settlement_values(name),
				)
			)
	return {
		"informante": {
			"IdInformante": (informante or {}).get("tax_id", ""),
			"razonSocial": (informante or {}).get("company_name", ""),
		},
		"purchases": purchases,
		"sales": sales,
		"exports": [],
		"cancelled": _annulled_vouchers(company, start, end),
	}


def generate_ats_files(company: str, year: int, month: int, reader=None) -> dict:
	"""Run read, collect, build, and zip for one fiscal month (whitelisted entry point).

	`reader` defaults to :func:`read_month` (bench); Ring-1 tests inject a
	synthetic reader. Returns `{"xml": str, "zip": bytes, "counts": {...}}`;
	persistence (File/download) belongs to the caller.
	"""
	from l10n_ec.sri.ats_builder import build_ats_xml, build_ats_zip
	from l10n_ec.sri.ats_collector import collect_month

	fetch = reader or read_month
	month_docs = fetch(company, year, month) or {}
	collected = collect_month(company, year, month, lambda c, y, m: month_docs)
	collected["informante"] = month_docs.get("informante") or {}
	period = f"{month:02d}{year}"
	xml = build_ats_xml(collected, period)
	return {
		"xml": xml,
		"zip": build_ats_zip(xml, period),
		"counts": {
			section: len(collected.get(section) or [])
			for section in ("compras", "ventas", "exportaciones", "anulados")
		},
	}
