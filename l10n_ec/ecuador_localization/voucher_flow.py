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

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri import xml_builder
from l10n_ec.sri.access_key import generate_access_key
from l10n_ec.sri.payment_methods import resolve_payment_method
from l10n_ec.sri.signer import sign_xml_xades_bes
from l10n_ec.sri.soap_client import (
	SriSoapClient,
	process_authorization_response,
	process_reception_response,
)
from l10n_ec.sri.tax_codes import tax_codes_for_template
from l10n_ec.sri.voucher_states import SriVoucherError, next_state
from l10n_ec.sri.withholding_concepts import validate_concepto_map

BUILDERS = {
	"01": "build_factura_xml",
	"03": "build_liquidacion_compra_xml",
	"04": "build_nota_credito_xml",
	"05": "build_nota_debito_xml",
	"06": "build_guia_xml",
	"07": "build_retencion_xml",
}

DOC_SCHEMAS = {
	"01": "factura",
	"03": "liquidacion_compra",
	"04": "nota_credito",
	"05": "nota_debito",
	"06": "guia",
	"07": "retencion",
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
	data: dict = {"issue_date": invoice.get("issue_date", ""), "subtotal": invoice.get("subtotal", 0.0)}
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
	elif cod_doc == "06":
		data.update(
			{
				"origin_address": invoice["origin_address"],
				"carrier_name": invoice["carrier_name"],
				"carrier_id_type": invoice["carrier_id_type"],
				"carrier_id": invoice["carrier_id"],
				"transport_start": invoice["transport_start"],
				"transport_end": invoice["transport_end"],
				"plate": invoice["plate"],
				"recipients": invoice["recipients"],
			}
		)
	elif cod_doc == "07":
		data.update(
			{
				"subject_id_type": invoice["subject_id_type"],
				"related_party": invoice.get("related_party", "NO"),
				"subject_name": invoice["subject_name"],
				"subject_id": invoice["subject_id"],
				"fiscal_period": invoice["fiscal_period"],
				"docs": invoice["docs"],
			}
		)
	else:
		raise SriVoucherError(_("Unsupported SRI document code '{}'.").format(cod_doc))
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
			doc.unsigned_xml.encode("utf-8") if isinstance(doc.unsigned_xml, str) else doc.unsigned_xml
		)
	except Exception as exc:
		raise xml_builder.SriXmlError(
			_("Generated XML is malformed: {}. Head: {!r}").format(exc, doc.unsigned_xml[:200])
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
	withholding_codes: dict | None = None,
	sustento_code: str = "02",
	guia_data: dict | None = None,
	payment_method: str = "01",
	iva_concepto: str | None = None,
) -> dict:
	"""Run generate/sign/submit/poll for one voucher; safe to re-run anytime."""
	resolve_payment_method(payment_method)
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to process vouchers.")
	doc = frappe.get_doc("SRI Electronic Voucher", voucher_name)
	if doc.voucher_state not in ("Generated", "Signed", "Received"):
		return {"ok": False, "skipped": f"process needs a live state, found {doc.voucher_state}"}
	if doc.voucher_state == "Generated":
		payload = _assemble_payload(
			doc,
			reason=reason,
			reasons=reasons,
			withholding_codes=withholding_codes,
			sustento_code=sustento_code,
			guia_data=guia_data,
			payment_method=payment_method,
			iva_concepto=iva_concepto,
		)
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
			_notify_authorized(doc)
			return polled
		max_polls -= 1
		if doc.voucher_state == "Received" and max_polls > 0:
			time.sleep(poll_interval)
	if doc.voucher_state == "Received":
		final = poll_voucher_doc(doc, client_ws=client_ws, environment=environment, max_attempts=1)
		if final["ok"]:
			_notify_authorized(doc)
		return final
	return {"ok": doc.voucher_state == "Authorized", "state": doc.voucher_state}


def _notify_authorized(doc) -> None:
	"""Queue the customer email; mail failures never undo the authorization."""
	try:
		from l10n_ec.ecuador_localization.voucher_mail import send_authorized_voucher_mail

		send_authorized_voucher_mail(doc.name)
	except Exception as exc:
		doc.last_message = f"{doc.last_message or ''} | mail skipped: {exc}".strip(" |")
		save_voucher(doc)


def enqueue_process_voucher(voucher_name: str, payment_method: str = "01") -> None:
	"""Enqueue asynchronous voucher processing (production entry point)."""
	resolve_payment_method(payment_method)
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to enqueue vouchers.")
	frappe.enqueue(
		"l10n_ec.ecuador_localization.voucher_flow.process_voucher",
		voucher_name=voucher_name,
		payment_method=payment_method,
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
	withholding_codes: dict | None = None,
	sustento_code: str = "02",
	guia_data: dict | None = None,
	payment_method: str = "01",
	iva_concepto: str | None = None,
	run_now: bool = False,
	key_material: tuple | None = None,
	client_ws=None,
) -> dict:
	"""Create a voucher for an invoice and process it (whitelisted entry point)."""
	resolve_payment_method(payment_method)
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to create vouchers.")
	ref = frappe.get_doc(reference_doctype, reference_name)
	cod_doc = sri_doc_code or _derive_cod_doc(reference_doctype, reference_name)
	emission, sequential = _resolve_emission_point(ref.company, cod_doc, emission_point)
	env = _resolve_environment(ref.company)
	number15 = f"{emission.establishment_code}{emission.emission_point_code}{sequential}"
	company_tax_id = frappe.db.get_value("Company", ref.company, "tax_id")
	if not company_tax_id:
		raise SriVoucherError(_("Company '{}' needs a tax_id (RUC) to emit vouchers.").format(ref.company))
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
			voucher.name,
			key_material=key_material,
			client_ws=client_ws,
			reason=reason,
			reasons=reasons,
			withholding_codes=withholding_codes,
			sustento_code=sustento_code,
			guia_data=guia_data,
			payment_method=payment_method,
			iva_concepto=iva_concepto,
		)
	enqueue_process_voucher(voucher.name, payment_method=payment_method)
	return {"ok": True, "voucher": voucher.name, "queued": True}


def _derive_cod_doc(reference_doctype: str, reference_name: str) -> str:
	"""Derive the SRI document code from the referenced invoice."""
	if reference_doctype == "Purchase Invoice":
		return "03"
	if reference_doctype == "Delivery Note":
		return "06"
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
			_("No SRI Emission Point for company '{}' and document '{}'.").format(company, cod_doc)
		)
	for row in emission.sequences:
		if row.document_type == cod_doc:
			row.current_sequence = (row.current_sequence or 0) + 1
			emission.save(ignore_permissions=True)
			return emission, f"{row.current_sequence:09d}"
	raise SriVoucherError(_("Emission point '{}' has no sequence for '{}'.").format(emission.name, cod_doc))


def _format_sri_number(establishment: str, emission_point: str, sequential: str) -> str:
	return f"{establishment}-{emission_point}-{sequential}"


def _resolve_environment(company: str) -> str:
	company_env = frappe.db.get_value("Company", company, "sri_environment")
	return ENVIRONMENTS.get(company_env or "Test", "test")


def _resolve_key_material(company: str) -> tuple:
	signature = frappe.db.get_value("Company", company, "sri_signature")
	if not signature:
		raise SriVoucherError(_("Company '{}' has no SRI Signature configured.").format(company))
	from l10n_ec.ecuador_localization.doctype.sri_signature.sri_signature import SRISignature

	sig_doc = frappe.get_doc("SRI Signature", signature)
	if not isinstance(sig_doc, SRISignature):  # pragma: no cover
		raise SriVoucherError(_("SRI Signature '{}' is not usable.").format(signature))
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


def sustento_entries(native_rows: list, purchase: dict, code_map: dict) -> list:
	"""Adapt native withholding rows to grouping inputs with explicit SRI codes.

	`native_rows` carry `category`, `rate`, `taxable`, `amount` (mirroring
	Tax Withholding Entry fields); `code_map` resolves category names to
	`(impuesto, codigoRetencion)` with no guessing inside. Unknown or
	pending concepto codes fail loud via `validate_concepto_map`.
	"""
	validate_concepto_map(code_map)
	adapted = []
	for row in native_rows:
		if row["category"] not in code_map:
			raise SriVoucherError(
				_("Withholding category '{}' has no SRI code mapping.").format(row["category"])
			)
		impuesto, codigo = code_map[row["category"]]
		adapted.append(
			{
				"purchase": purchase,
				"tax_type": "IR" if impuesto == "1" else "IVA",
				"withholding_code": codigo,
				"rate": row["rate"],
				"base": row["taxable"],
				"value": row["amount"],
			}
		)
	return adapted


def group_withholdings_by_sustento(withholdings: list, sustento_code: str = "02") -> list:
	"""Group native withholding lines into SRI `docSustento` blocks.

	Each input carries `purchase` (doc identity + code-shaped `doc_taxes` +
	`payments`), `tax_type` (`IR`/`IVA`), `withholding_code` (SRI percentage
	code), and `rate`/`base`/`value`. Purchases group by document; taxes map
	`IR`→`1`, anything else→`2`.
	"""
	groups: dict = {}
	for item in withholdings:
		purchase = item["purchase"]
		key = (purchase["doc_code"], purchase["number"])
		group = groups.setdefault(key, {"purchase": purchase, "retenciones": []})
		group["retenciones"].append(
			{
				"code": "1" if item["tax_type"] == "IR" else "2",
				"withholding_code": item["withholding_code"],
				"base": item["base"],
				"rate": item["rate"],
				"value": item["value"],
			}
		)
	blocks = []
	for purchase, group in ((g["purchase"], g) for g in groups.values()):
		blocks.append(
			{
				"sustento_code": sustento_code,
				"doc_code": purchase["doc_code"],
				"doc_number": purchase["number"],
				"issue_date": purchase["issue_date"],
				"auth_number": purchase["auth_number"],
				"subtotal": purchase["subtotal"],
				"total": purchase["total"],
				"doc_taxes": purchase["doc_taxes"],
				"withholdings": group["retenciones"],
				"payments": purchase.get("payments", []),
			}
		)
	return blocks


def _assemble_payload(
	doc,
	reason=None,
	reasons=None,
	withholding_codes=None,
	sustento_code="02",
	guia_data=None,
	payment_method="01",
	iva_concepto=None,
):
	"""Build the builder payload from live Company/invoice documents."""
	company = frappe.get_doc("Company", doc.company)
	if not getattr(company, "tax_id", None):
		raise SriVoucherError(_("Company '{}' needs a tax_id (RUC) to emit vouchers.").format(doc.company))
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
	resolve_payment_method(payment_method)
	invoice = _invoice_dict(
		doc,
		reason=reason,
		reasons=reasons,
		withholding_codes=withholding_codes,
		sustento_code=sustento_code,
		guia_data=guia_data,
		payment_method=payment_method,
		iva_concepto=iva_concepto,
	)
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


def _invoice_dict(
	doc,
	reason=None,
	reasons=None,
	withholding_codes=None,
	sustento_code="02",
	guia_data=None,
	payment_method="01",
	iva_concepto=None,
) -> dict:
	"""Map a live invoice document to the normalized payload dict."""
	resolve_payment_method(payment_method)
	ref = frappe.get_doc(doc.reference_doctype, doc.reference_name)
	base: dict = {
		"doctype": doc.reference_doctype,
		"cod_doc": doc.sri_doc_code,
		"issue_date": ref.posting_date.strftime("%d/%m/%Y"),
		"subtotal": ref.total,
		"discount": ref.discount_amount or 0.0,
		"total": ref.grand_total,
		"payments": [{"method": payment_method, "amount": ref.grand_total}],
		"lines": [_invoice_line(row) for row in ref.items],
	}
	if doc.sri_doc_code == "06":
		if guia_data is None:
			raise SriVoucherError(_("Delivery notes need explicit guia_data {carrier, transport, docs}."))
		base.update(_guia_recipient_and_carrier(doc, ref, guia_data))
		return base
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
			raise SriVoucherError(_("Debit notes need explicit reasons [{razon, valor}]."))
		base.update({"taxes": base.pop("tax_totals"), "total_value": ref.grand_total, "reasons": reasons})
	if doc.sri_doc_code == "07":
		if withholding_codes is None:
			raise SriVoucherError(
				_("Withholding vouchers need explicit withholding_codes {category: (impuesto, codigo)}.")
			)
		base.update(
			_withholding_subject_and_docs(
				doc, ref, withholding_codes, sustento_code, payment_method, iva_concepto
			)
		)
	return base


def _synthesize_iva_row(mapped_lines: list, iva_concepto: str) -> dict | None:
	"""Synthesize one IVA withholding row from IVA line taxes (ERPNext gap).

	ERPNext only computes Net/Gross-basis withholdings, so IVA (tax-on-tax)
	categories must never be assigned natively (see the Supplier guard).
	At emission, the IVA base is the sum of IVA (`code == "2"`) line taxes
	and the rate comes from the caller-chosen IVA concepto; zero base emits
	nothing.
	"""
	from l10n_ec.sri.withholding_concepts import resolve_concepto

	impuesto, rate, _description = resolve_concepto(iva_concepto)
	if impuesto != "2":
		raise SriVoucherError(_("IVA withholding needs an IVA concepto, got '{}'.").format(iva_concepto))
	base = round(sum(tax["value"] for line in mapped_lines for tax in line["taxes"] if tax["code"] == "2"), 2)
	if not base:
		return None
	return {
		"category": f"Ecuador IVA {rate:g}%",
		"rate": rate,
		"taxable": base,
		"amount": round(base * rate / 100, 2),
	}


def _withholding_subject_and_docs(
	doc,
	ref,
	withholding_codes: dict,
	sustento_code: str,
	payment_method: str = "01",
	iva_concepto: str | None = None,
) -> dict:
	"""Build the 07 subject block plus grouped sustento docs from native entries."""
	resolve_payment_method(payment_method)
	mapped = [map_line_taxes(line) for line in base_lines(ref)]
	doc_taxes = [
		{
			"tax_code": tax["code"],
			"rate_code": tax["rate_code"],
			"base": tax["base"],
			"rate": tax["rate"],
			"tax_value": tax["value"],
		}
		for line in mapped
		for tax in line["taxes"]
	]
	purchase = {
		"doc_code": "01",
		"number": ref.bill_no,
		"issue_date": ref.posting_date.strftime("%d/%m/%Y"),
		"auth_number": "0000000000",
		"subtotal": ref.total,
		"total": ref.grand_total,
		"doc_taxes": doc_taxes,
		"payments": [{"method": payment_method, "amount": ref.grand_total}],
	}
	native = [
		{
			"category": row.tax_withholding_category,
			"rate": row.tax_rate,
			"taxable": row.taxable_amount,
			"amount": row.withholding_amount,
		}
		for row in ref.tax_withholding_entries
	]
	if iva_concepto is not None:
		synthesized = _synthesize_iva_row(mapped, iva_concepto)
		if synthesized is not None:
			native.append(synthesized)
	inputs = sustento_entries(native, purchase, withholding_codes)
	party = frappe.db.get_value(
		"Supplier", ref.supplier, ["sri_identification_type", "tax_id", "supplier_name"], as_dict=True
	)
	return {
		"subject_id_type": party.sri_identification_type,
		"subject_name": party.supplier_name,
		"subject_id": party.tax_id,
		"fiscal_period": ref.posting_date.strftime("%m/%Y"),
		"docs": group_withholdings_by_sustento(inputs, sustento_code=sustento_code),
	}


def _guia_recipient_and_carrier(doc, ref, guia_data: dict) -> dict:
	"""Build the 06 carrier block plus single recipient from a Delivery Note."""
	required = {
		"carrier_name",
		"carrier_id_type",
		"carrier_id",
		"origin_address",
		"transport_start",
		"transport_end",
		"plate",
		"transfer_reason",
	}
	missing = sorted(required - set(guia_data))
	if missing:
		raise SriVoucherError(_("guia_data is missing keys: {}.").format(", ".join(missing)))
	docs = guia_data.get("docs", [])
	if len(docs) != 1:
		raise SriVoucherError(_("Delivery notes need exactly one sustento doc in guia_data['docs']."))
	party = frappe.db.get_value(
		"Customer", ref.customer, ["sri_identification_type", "tax_id", "customer_name"], as_dict=True
	)
	if not ref.shipping_address_name:
		raise SriVoucherError(
			_("Delivery Note '{}' needs a shipping address for the guia recipient.").format(ref.name)
		)
	address = frappe.get_doc("Address", ref.shipping_address_name)
	recipient_address = address.address_line1
	if getattr(address, "city", None):
		recipient_address += f", {address.city}"
	sustento = docs[0]
	sustento_auth = sustento.get("auth_number", "")
	sustento_date = sustento.get("doc_issue_date", "")
	return {
		"origin_address": guia_data["origin_address"],
		"carrier_name": guia_data["carrier_name"],
		"carrier_id_type": guia_data["carrier_id_type"],
		"carrier_id": guia_data["carrier_id"],
		"transport_start": guia_data["transport_start"],
		"transport_end": guia_data["transport_end"],
		"plate": guia_data["plate"],
		"recipients": [
			{
				"recipient_id": party.tax_id,
				"recipient_name": party.customer_name,
				"recipient_address": recipient_address,
				"transfer_reason": guia_data["transfer_reason"],
				"route": guia_data.get("route", ""),
				"doc_code": sustento["doc_code"],
				"doc_number": sustento["doc_number"],
				"auth_number": sustento_auth,
				"doc_issue_date": sustento_date,
				"lines": [
					{
						"code": row.item_code,
						"aux_code": "",
						"description": row.description,
						"qty": row.qty,
					}
					for row in ref.items
				],
			}
		],
	}


def base_lines(ref) -> list:
	"""Normalized template-style lines for sustento doc taxes."""
	lines = []
	for row in ref.items:
		taxes = []
		if getattr(row, "item_tax_template", None):
			rate = _template_rate(row.item_tax_template)
			taxes.append(
				{
					"template": row.item_tax_template,
					"rate": rate,
					"base": row.amount,
					"value": round(row.amount * rate / 100, 2),
				}
			)
		lines.append(
			{
				"code": row.item_code,
				"aux_code": "",
				"description": row.description,
				"qty": row.qty,
				"unit_price": row.rate,
				"discount": row.discount_amount or 0.0,
				"subtotal": row.amount,
				"taxes": taxes,
			}
		)
	return lines


def _template_rate(template_title: str) -> float:
	"""Look up an Item Tax Template rate by title."""
	template = frappe.get_doc("Item Tax Template", template_title)
	return template.taxes[0].tax_rate if template.taxes else 0.0


def _original_voucher(ref) -> dict:
	"""Locate the authorized voucher of the modified invoice."""
	name = frappe.db.get_value(
		"SRI Electronic Voucher",
		{"reference_doctype": ref.doctype, "reference_name": ref.return_against},
		"name",
	)
	if not name:
		raise SriVoucherError(_("No voucher found for modified document '{}'.").format(ref.return_against))
	voucher = frappe.get_doc("SRI Electronic Voucher", name)
	original = frappe.get_doc(ref.doctype, ref.return_against)
	return {
		"cod_doc": voucher.sri_doc_code,
		"number": voucher.sri_number,
		"date": original.posting_date.strftime("%d/%m/%Y"),
	}
