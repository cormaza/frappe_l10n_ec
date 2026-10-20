"""SRI voucher submit/poll pipeline (frappe-side orchestration).

Pure mapping (`map_line_taxes`, `build_voucher_payload`) stays testable in
Ring 1. `*_doc` functions mutate in-memory documents; `*_voucher` wrappers
load and save by name for workers and whitelisted calls. Pass explicit fakes
(`client_ws`, `key_material`) in tests; production resolves everything from
the voucher's company. Re-running any step in the wrong state returns a skip
instead of raising, so retries and double submits are idempotent.
"""

import time
from datetime import date

from lxml import etree

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

from l10n_ec.sri import xml_builder
from l10n_ec.sri.access_key import generate_access_key
from l10n_ec.sri.signer import sign_xml_xades_bes
from l10n_ec.sri.soap_client import (
	SriSoapClient,
	process_authorization_response,
	process_reception_response,
)
from l10n_ec.sri.tax_codes import tax_codes_for_template
from l10n_ec.sri.voucher_states import SriVoucherError, next_state

BUILDERS = {
	"01": "build_factura_xml",
	"03": "build_liquidacion_compra_xml",
	"04": "build_nota_credito_xml",
	"05": "build_nota_debito_xml",
}

DOC_SCHEMAS = {
	"01": "factura",
	"03": "liquidacion_compra",
	"04": "nota_credito",
	"05": "nota_debito",
}

ENVIRONMENTS = {"Test": "test", "Production": "production"}


def _map_taxes(taxes: list) -> list:
	"""Resolve template titles to SRI codes, keeping rate/base/value."""
	mapped = []
	for tax in taxes:
		code, rate_code = tax_codes_for_template(tax["template"])
		mapped.append(
			{
				"code": code,
				"rate_code": rate_code,
				"rate": tax.get("rate"),
				"base": tax["base"],
				"value": tax["value"],
			}
		)
	return mapped


def map_line_taxes(line: dict) -> dict:
	"""Resolve template titles in one line to SRI `(code, rate_code)` pairs."""
	taxes = []
	for tax in line.get("taxes", []):
		code, rate_code = tax_codes_for_template(tax["template"])
		taxes.append(
			{
				"code": code,
				"rate_code": rate_code,
				"rate": tax["rate"],
				"base": tax["base"],
				"value": tax["value"],
			}
		)
	out = dict(line)
	out["taxes"] = taxes
	return out


def map_tax_totals(totals: list) -> list:
	"""Resolve template titles in totals rows to SRI codes."""
	return _map_taxes(totals)


def build_voucher_payload(invoice: dict, emitter: dict, sequence: dict) -> dict:
	"""Assemble `(builder, ctx, data)` for the voucher builders from plain dicts.

	`invoice` carries normalized lines (`taxes` reference template titles);
	`emitter` carries company data; `sequence` carries the 9-digit sequential
	and the 49-digit access key.
	"""
	cod_doc = invoice["cod_doc"]
	ctx = {
		"environment": emitter["environment"],
		"doc_code": cod_doc,
		"ruc": emitter["ruc"],
		"legal_name": emitter["legal_name"],
		"trade_name": emitter.get("trade_name", ""),
		"head_office_address": emitter["head_office_address"],
		"establishment": emitter["establishment"],
		"emission_point": emitter["emission_point"],
		"sequential": sequence["sequential"],
		"access_key": sequence["access_key"],
		"branch_address": emitter["branch_address"],
		"special_taxpayer": emitter.get("special_taxpayer", ""),
		"accounting_required": emitter.get("accounting_required", False),
	}
	lines = [map_line_taxes(line) for line in invoice.get("lines", [])]
	totals = map_tax_totals(invoice.get("tax_totals", []))
	data: dict = {"issue_date": invoice["issue_date"], "subtotal": invoice["subtotal"]}
	if cod_doc == "01":
		data.update(
			{
				"buyer_id_type": invoice["buyer_id_type"],
				"buyer_name": invoice["buyer_name"],
				"buyer_id": invoice["buyer_id"],
				"buyer_address": invoice.get("buyer_address", ""),
				"discount": invoice.get("discount", 0.0),
				"tax_totals": totals,
				"tip": invoice.get("tip", 0.0),
				"total": invoice["total"],
				"payments": invoice.get("payments", []),
				"lines": lines,
			}
		)
	elif cod_doc == "03":
		data.update(
			{
				"supplier_id_type": invoice["supplier_id_type"],
				"supplier_name": invoice["supplier_name"],
				"supplier_id": invoice["supplier_id"],
				"supplier_address": invoice.get("supplier_address", ""),
				"discount": invoice.get("discount", 0.0),
				"tax_totals": totals,
				"total": invoice["total"],
				"payments": invoice.get("payments", []),
				"lines": lines,
			}
		)
	elif cod_doc == "04":
		data.update(
			{
				"buyer_id_type": invoice["buyer_id_type"],
				"buyer_name": invoice["buyer_name"],
				"buyer_id": invoice["buyer_id"],
				"modified_doc_code": invoice["modified_doc_code"],
				"modified_doc_number": invoice["modified_doc_number"],
				"sustento_issue_date": invoice["sustento_issue_date"],
				"adjustment_value": invoice["adjustment_value"],
				"tax_totals": totals,
				"reason": invoice["reason"],
				"lines": lines,
			}
		)
	elif cod_doc == "05":
		data.update(
			{
				"buyer_id_type": invoice["buyer_id_type"],
				"buyer_name": invoice["buyer_name"],
				"buyer_id": invoice["buyer_id"],
				"modified_doc_code": invoice["modified_doc_code"],
				"modified_doc_number": invoice["modified_doc_number"],
				"sustento_issue_date": invoice["sustento_issue_date"],
				"taxes": _map_taxes(invoice["taxes"]),
				"total_value": invoice["total_value"],
				"reasons": invoice.get("reasons", []),
			}
		)
	else:
		raise SriVoucherError(f"Unsupported SRI document code '{cod_doc}'.")
	return {"builder": BUILDERS[cod_doc], "schema": DOC_SCHEMAS[cod_doc], "ctx": ctx, "data": data}


def apply_transition(doc, event: str, message: str = "") -> str:
	"""Move an in-memory voucher to the next state (no save)."""
	doc.voucher_state = next_state(doc.voucher_state, event)
	if message:
		doc.last_message = message
	return doc.voucher_state


def generate_voucher_xml_doc(doc, payload: dict) -> dict:
	"""Build the unsigned XML for a Generated voucher (no save)."""
	if doc.voucher_state != "Generated":
		return {"ok": False, "skipped": f"generate needs Generated, found {doc.voucher_state}"}
	builder = getattr(xml_builder, payload["builder"])
	doc.unsigned_xml = builder(payload["ctx"], payload["data"])
	xml_builder.validate_against_xsd(doc.unsigned_xml, payload["schema"])
	try:
		etree.fromstring(
			doc.unsigned_xml.encode("utf-8")
			if isinstance(doc.unsigned_xml, str)
			else doc.unsigned_xml
		)
	except Exception as exc:
		raise xml_builder.SriXmlError(
			f"Generated XML is malformed: {exc}. Head: {doc.unsigned_xml[:200]!r}"
		)
	return {"ok": True, "state": doc.voucher_state}


def sign_voucher_doc(doc, key_material: tuple | None = None) -> dict:
	"""XAdES-sign a Generated voucher (no save)."""
	if doc.voucher_state != "Generated":
		return {"ok": False, "skipped": f"sign needs Generated, found {doc.voucher_state}"}
	if not getattr(doc, "unsigned_xml", None):
		return {"ok": False, "skipped": "sign needs generated XML first"}
	if key_material is None:
		key_material = _resolve_key_material(doc.company)
	p12_bytes, password = key_material
	try:
		xml_content = read_voucher_xml(doc, "unsigned_xml")
		doc.signed_xml = sign_xml_xades_bes(xml_content, file_content=p12_bytes, password=password)
	except Exception as exc:
		raise SriVoucherError(
			f"Signing failed in state {doc.voucher_state}: {exc}. XML head: {str(doc.unsigned_xml)[:200]!r}"
		)
	apply_transition(doc, "sign")
	return {"ok": True, "state": doc.voucher_state}


def submit_voucher_doc(doc, client_ws=None, environment: str | None = None) -> dict:
	"""Submit a Signed voucher to SRI reception (no save)."""
	if doc.voucher_state != "Signed":
		return {"ok": False, "skipped": f"submit needs Signed, found {doc.voucher_state}"}
	if client_ws is None:
		environment = environment or _resolve_environment(doc.company)
		wsdl = SriSoapClient(environment=environment)
		client_ws = wsdl.create_client("reception")
	response = SriSoapClient.send_xml_for_reception(client_ws, read_voucher_xml(doc, "signed_xml"))
	ok, messages = process_reception_response(response)
	apply_transition(doc, "receive_ok" if ok else "receive_fail", message=" | ".join(messages))
	return {"ok": ok, "state": doc.voucher_state, "messages": messages}


def poll_voucher_doc(doc, client_ws=None, environment: str | None = None, max_attempts: int = 5) -> dict:
	"""Poll SRI authorization for a Received voucher (no save, no sleep)."""
	if doc.voucher_state != "Received":
		return {"ok": False, "skipped": f"poll needs Received, found {doc.voucher_state}"}
	if client_ws is None:
		environment = environment or _resolve_environment(doc.company)
		wsdl = SriSoapClient(environment=environment)
		client_ws = wsdl.create_client("authorization")
	messages: list = []
	for _ in range(max_attempts):
		response = SriSoapClient.request_authorization(client_ws, doc.access_key)
		authorized, messages, auth_values = process_authorization_response(response, doc.access_key)
		if authorized:
			doc.authorization_number = auth_values.get("l10n_ec_xml_access_key", doc.access_key)
			doc.authorization_date = auth_values.get("l10n_ec_authorization_date")
			apply_transition(doc, "authorize_ok")
			return {"ok": True, "state": doc.voucher_state, "messages": messages}
	apply_transition(doc, "authorize_fail", message=" | ".join(messages))
	return {"ok": False, "state": doc.voucher_state, "messages": messages}


def save_voucher(doc):
	"""Persist a voucher document (frappe only)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to save vouchers.")
	doc.save(ignore_permissions=True)
	return doc


def persist_voucher_xml(doc, fieldname: str) -> str:
	"""Store a voucher XML string as a private File; set the field to its URL.

	Raw XML must never live in DocType text fields: Frappe sanitizes them
	on save (bleach), corrupting the document.
	"""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to attach voucher files.")
	content = getattr(doc, fieldname)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{doc.access_key}-{fieldname.replace('_xml', '')}.xml",
			"content": content.encode("utf-8") if isinstance(content, str) else content,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)
	setattr(doc, fieldname, file_doc.file_url)
	return file_doc.file_url


def read_voucher_xml(doc, fieldname: str) -> str:
	"""Read voucher XML back, from a File URL or a raw in-memory string."""
	value = getattr(doc, fieldname) or ""
	if isinstance(value, str) and value.startswith("/"):
		if frappe is None:  # pragma: no cover
			raise RuntimeError("frappe is required to read attached voucher files.")
		file_name = frappe.db.get_value("File", {"file_url": value}, "name")
		content = frappe.get_doc("File", file_name).get_content()
		return content if isinstance(content, str) else content.decode("utf-8")
	return value


def process_voucher(
	voucher_name: str,
	key_material: tuple | None = None,
	client_ws=None,
	environment: str | None = None,
	max_polls: int = 5,
	poll_interval: int = 10,
	reason: str | None = None,
	reasons: list | None = None,
) -> dict:
	"""Run generate/sign/submit/poll for one voucher; safe to re-run anytime."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to process vouchers.")
	doc = frappe.get_doc("SRI Electronic Voucher", voucher_name)
	if doc.voucher_state not in ("Generated", "Signed", "Received"):
		return {"ok": False, "skipped": f"process needs a live state, found {doc.voucher_state}"}
	if doc.voucher_state == "Generated":
		payload = _assemble_payload(doc, reason=reason, reasons=reasons)
		generated = generate_voucher_xml_doc(doc, payload)
		if not generated["ok"]:
			return generated
		persist_voucher_xml(doc, "unsigned_xml")
		save_voucher(doc)
		signed = sign_voucher_doc(doc, key_material=key_material)
		if not signed["ok"]:
			return signed
		persist_voucher_xml(doc, "signed_xml")
		save_voucher(doc)
	if doc.voucher_state == "Signed":
		submitted = submit_voucher_doc(doc, client_ws=client_ws, environment=environment)
		save_voucher(doc)
		if not submitted["ok"]:
			return submitted
	while doc.voucher_state == "Received" and max_polls > 0:
		polled = poll_voucher_doc(doc, client_ws=client_ws, environment=environment, max_attempts=1)
		save_voucher(doc)
		if polled["ok"]:
			return polled
		max_polls -= 1
		if doc.voucher_state == "Received" and max_polls > 0:
			time.sleep(poll_interval)
	if doc.voucher_state == "Received":
		return poll_voucher_doc(doc, client_ws=client_ws, environment=environment, max_attempts=1)
	return {"ok": doc.voucher_state == "Authorized", "state": doc.voucher_state}


def enqueue_process_voucher(voucher_name: str) -> None:
	"""Enqueue asynchronous voucher processing (production entry point)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to enqueue vouchers.")
	frappe.enqueue(
		"l10n_ec.ecuador_localization.voucher_flow.process_voucher",
		voucher_name=voucher_name,
		enqueue_after_commit=True,
	)


@frappe.whitelist() if frappe else (lambda f: f)
def create_and_process(
	reference_doctype: str,
	reference_name: str,
	sri_doc_code: str | None = None,
	emission_point: str | None = None,
	reason: str | None = None,
	reasons: list | None = None,
	run_now: bool = False,
	key_material: tuple | None = None,
	client_ws=None,
) -> dict:
	"""Create a voucher for an invoice and process it (whitelisted entry point)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to create vouchers.")
	ref = frappe.get_doc(reference_doctype, reference_name)
	cod_doc = sri_doc_code or _derive_cod_doc(reference_doctype, reference_name)
	emission, sequential = _resolve_emission_point(ref.company, cod_doc, emission_point)
	env = _resolve_environment(ref.company)
	number15 = f"{emission.establishment_code}{emission.emission_point_code}{sequential}"
	company_tax_id = frappe.db.get_value("Company", ref.company, "tax_id")
	if not company_tax_id:
		raise SriVoucherError(f"Company '{ref.company}' needs a tax_id (RUC) to emit vouchers.")
	issue_date = ref.posting_date.date() if hasattr(ref.posting_date, "date") else ref.posting_date
	access_key = generate_access_key(
		cod_doc, number15, "1" if env == "test" else "2", issue_date, company_tax_id
	)
	voucher = frappe.get_doc(
		{
			"doctype": "SRI Electronic Voucher",
			"access_key": access_key,
			"sri_number": _format_sri_number(
				emission.establishment_code, emission.emission_point_code, sequential
			),
			"voucher_state": "Generated",
			"sri_doc_code": cod_doc,
			"company": ref.company,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	voucher.insert(ignore_permissions=True)
	if run_now:
		return process_voucher(
			voucher.name, key_material=key_material, client_ws=client_ws, reason=reason, reasons=reasons
		)
	enqueue_process_voucher(voucher.name)
	return {"ok": True, "voucher": voucher.name, "queued": True}


def _derive_cod_doc(reference_doctype: str, reference_name: str) -> str:
	"""Derive the SRI document code from the referenced invoice."""
	if reference_doctype == "Purchase Invoice":
		return "03"
	ref = frappe.get_doc(reference_doctype, reference_name)
	if getattr(ref, "is_debit_note", None):
		return "05"
	if getattr(ref, "is_return", None):
		return "04"
	return "01"


def _resolve_emission_point(company: str, cod_doc: str, emission_point: str | None = None):
	"""Find the emission point and bump its sequence row for `cod_doc`."""
	if emission_point:
		emission = frappe.get_doc("SRI Emission Point", emission_point)
	else:
		candidates = frappe.get_all("SRI Emission Point", filters={"company": company}, pluck="name")
		emission = None
		for name in candidates:
			candidate = frappe.get_doc("SRI Emission Point", name)
			if any(row.document_type == cod_doc for row in (candidate.sequences or [])):
				emission = candidate
				break
	if emission is None:
		raise SriVoucherError(
			f"No SRI Emission Point for company '{company}' and document '{cod_doc}'."
		)
	for row in emission.sequences:
		if row.document_type == cod_doc:
			row.current_sequence = (row.current_sequence or 0) + 1
			emission.save(ignore_permissions=True)
			return emission, f"{row.current_sequence:09d}"
	raise SriVoucherError(f"Emission point '{emission.name}' has no sequence for '{cod_doc}'.")


def _format_sri_number(establishment: str, emission_point: str, sequential: str) -> str:
	return f"{establishment}-{emission_point}-{sequential}"


def _resolve_environment(company: str) -> str:
	company_env = frappe.db.get_value("Company", company, "sri_environment")
	return ENVIRONMENTS.get(company_env or "Test", "test")


def _resolve_key_material(company: str) -> tuple:
	signature = frappe.db.get_value("Company", company, "sri_signature")
	if not signature:
		raise SriVoucherError(f"Company '{company}' has no SRI Signature configured.")
	from l10n_ec.ecuador_localization.doctype.sri_signature.sri_signature import SRISignature

	sig_doc = frappe.get_doc("SRI Signature", signature)
	if not isinstance(sig_doc, SRISignature):  # pragma: no cover
		raise SriVoucherError(f"SRI Signature '{signature}' is not usable.")
	return sig_doc._get_p12_bytes(), sig_doc._get_signing_password()


def aggregate_raw_totals(lines: list) -> list:
	"""Aggregate raw line taxes by template title, summing base/value."""
	grouped: dict = {}
	for line in lines:
		for tax in line.get("taxes", []):
			key = tax["template"]
			entry = grouped.setdefault(key, {"template": key, "base": 0.0, "value": 0.0})
			entry["base"] = round(entry["base"] + tax["base"], 2)
			entry["value"] = round(entry["value"] + tax["value"], 2)
	return list(grouped.values())


def _assemble_payload(doc, reason=None, reasons=None):
	"""Build the builder payload from live Company/invoice documents."""
	company = frappe.get_doc("Company", doc.company)
	if not getattr(company, "tax_id", None):
		raise SriVoucherError(f"Company '{doc.company}' needs a tax_id (RUC) to emit vouchers.")
	env = _resolve_environment(doc.company)
	estab, pto, sequential = doc.sri_number.split("-")
	address = _company_address_line(company)
	emitter = {
		"environment": "1" if env == "test" else "2",
		"ruc": company.tax_id,
		"legal_name": company.company_name,
		"trade_name": "",
		"head_office_address": address,
		"establishment": estab,
		"emission_point": pto,
		"branch_address": address,
		"special_taxpayer": getattr(company, "special_taxpayer_resolution", "") or "",
		"accounting_required": bool(getattr(company, "accounting_required", False)),
	}
	sequence = {"sequential": sequential, "access_key": doc.access_key}
	invoice = _invoice_dict(doc, reason=reason, reasons=reasons)
	return build_voucher_payload(invoice, emitter, sequence)


def _company_address_line(company) -> str:
	address_name = _default_company_address(company.name)
	if not address_name:
		return ""
	return frappe.db.get_value("Address", address_name, "address_line1") or ""


def _default_company_address(company: str):
	from frappe.contacts.doctype.address.address import get_default_address

	return get_default_address("Company", company)


def _invoice_line(row) -> dict:
	taxes = []
	if getattr(row, "item_tax_template", None):
		template = frappe.get_doc("Item Tax Template", row.item_tax_template)
		rate = template.taxes[0].tax_rate if template.taxes else 0.0
		taxes = [
			{
				"template": row.item_tax_template,
				"rate": rate,
				"base": row.amount,
				"value": round(row.amount * rate / 100, 2),
			}
		]
	return {
		"code": row.item_code,
		"aux_code": "",
		"description": row.description,
		"qty": row.qty,
		"unit_price": row.rate,
		"discount": row.discount_amount or 0.0,
		"subtotal": row.amount,
		"taxes": taxes,
	}


def _invoice_dict(doc, reason=None, reasons=None) -> dict:
	"""Map a live invoice document to the normalized payload dict."""
	ref = frappe.get_doc(doc.reference_doctype, doc.reference_name)
	base: dict = {
		"doctype": doc.reference_doctype,
		"cod_doc": doc.sri_doc_code,
		"issue_date": ref.posting_date.strftime("%d/%m/%Y"),
		"subtotal": ref.total,
		"discount": ref.discount_amount or 0.0,
		"total": ref.grand_total,
		"payments": [{"method": "01", "amount": ref.grand_total}],
		"lines": [_invoice_line(row) for row in ref.items],
	}
	if doc.sri_doc_code in ("01", "04", "05"):
		party = frappe.db.get_value(
			"Customer", ref.customer, ["sri_identification_type", "tax_id", "customer_name"], as_dict=True
		)
		base.update(
			{
				"buyer_id_type": party.sri_identification_type,
				"buyer_name": party.customer_name,
				"buyer_id": party.tax_id,
				"buyer_address": "",
			}
		)
	else:
		party = frappe.db.get_value(
			"Supplier", ref.supplier, ["sri_identification_type", "tax_id", "supplier_name"], as_dict=True
		)
		base.update(
			{
				"supplier_id_type": party.sri_identification_type,
				"supplier_name": party.supplier_name,
				"supplier_id": party.tax_id,
				"supplier_address": "",
			}
		)
	base["tax_totals"] = aggregate_raw_totals(base["lines"])
	if doc.sri_doc_code in ("04", "05"):
		original = _original_voucher(ref)
		base.update(
			{
				"modified_doc_code": original["cod_doc"],
				"modified_doc_number": original["number"],
				"sustento_issue_date": original["date"],
			}
		)
	if doc.sri_doc_code == "04":
		base.update(
			{"adjustment_value": abs(ref.grand_total), "reason": reason or "Devolucion de mercaderia"}
		)
	if doc.sri_doc_code == "05":
		if not reasons:
			raise SriVoucherError("Debit notes need explicit reasons [{razon, valor}].")
		base.update(
			{"taxes": base.pop("tax_totals"), "total_value": ref.grand_total, "reasons": reasons}
		)
	return base


def _original_voucher(ref) -> dict:
	"""Locate the authorized voucher of the modified invoice."""
	name = frappe.db.get_value(
		"SRI Electronic Voucher",
		{"reference_doctype": ref.doctype, "reference_name": ref.return_against},
		"name",
	)
	if not name:
		raise SriVoucherError(f"No voucher found for modified document '{ref.return_against}'.")
	voucher = frappe.get_doc("SRI Electronic Voucher", name)
	original = frappe.get_doc(ref.doctype, ref.return_against)
	return {
		"cod_doc": voucher.sri_doc_code,
		"number": voucher.sri_number,
		"date": original.posting_date.strftime("%d/%m/%Y"),
	}
