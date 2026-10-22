"""Contact tax identification hook contract for Customer/Supplier validation.

Phase 3 wiring calls :func:`validate_contact_tax_id` from the `validate` hook
and converts the `ValueError` into `frappe.throw`. Gating uses the Country
ISO code (`EC`), resolved from the contact address by the caller, so this
module stays free of `frappe` imports and testable in Ring 1.
"""

from l10n_ec.sri.identification import FINAL_CONSUMER_ID, validate_identification

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


ECUADOR_COUNTRY_CODE = "EC"
FINAL_CONSUMER_THRESHOLD = 50.00


def is_ecuadorian_contact(country_code: str | None) -> bool:
	"""Whether contact-level SRI validation applies, gated by Country ISO code."""
	return (country_code or "").strip().upper() == ECUADOR_COUNTRY_CODE


def is_foreign_contact(country_code: str | None) -> bool:
	"""Whether the contact is identifiably foreign (resolved non-EC ISO code).

	An unresolvable country (None/empty) is unknown, not foreign. Resolve it
	from the primary Address Country; never from Territory, which is a sales
	concept, not a nationality.
	"""
	code = (country_code or "").strip().upper()
	return bool(code) and code != ECUADOR_COUNTRY_CODE


def is_generic_final_consumer(identification_type_code: str | None, tax_id: str | None) -> bool:
	"""Whether the record is the generic final consumer (type or ID), all spellings."""
	code = (identification_type_code or "").strip()
	cleaned = (tax_id or "").strip()
	return code == "07" or cleaned == FINAL_CONSUMER_ID


def validate_contact_tax_id(
	country_code: str | None,
	identification_type_code: str | None,
	tax_id: str | None,
) -> None:
	"""Validate a contact tax ID, skipping non-Ecuadorian contacts silently.

	Raises `ValueError` with an English message when an Ecuadorian contact
	carries an invalid identification number.
	"""
	if not is_ecuadorian_contact(country_code):
		return
	if not validate_identification(identification_type_code or "", tax_id or ""):
		raise ValueError(
			_("Invalid tax identification '{}' for type '{}'.").format(
				(tax_id or "").strip(), (identification_type_code or "").strip()
			)
		)


def validate_final_consumer_amount(
	identification_type_code: str | None,
	tax_id: str | None,
	total: float | None,
	threshold: float = FINAL_CONSUMER_THRESHOLD,
) -> None:
	"""Reject over-threshold invoices to the generic final consumer.

	Only the generic consumer identity (type `07` or the fixed ID) is
	checked; identified buyers are unaffected. Multi-currency conversion
	is out of scope: totals compare directly against the USD threshold.
	"""
	if not is_generic_final_consumer(identification_type_code, tax_id):
		return
	if (total or 0) > threshold:
		raise ValueError(
			_(
				"Sales to Consumidor Final above {} are not allowed; register the buyer identification."
			).format(threshold)
		)


def validate_pos_tickets(
	identification_type_code: str | None,
	tax_id: str | None,
	ticket_totals: list,
	threshold: float = FINAL_CONSUMER_THRESHOLD,
) -> None:
	"""Reject any over-threshold POS ticket to the generic final consumer.

	A consolidated Sales Invoice sums N tickets, so the sum is never the
	transaction: each ticket total is checked instead. Only the generic
	consumer identity is checked; identified buyers are unaffected.
	"""
	if not is_generic_final_consumer(identification_type_code, tax_id):
		return
	for ticket_total in ticket_totals or []:
		if (ticket_total or 0) > threshold:
			raise ValueError(
				_(
					"POS ticket to Consumidor Final above {} is not allowed; register the buyer identification."
				).format(threshold)
			)


TAX_DESCRIPTIONS = {
	"1010504": "IVA Pagado",
	"2010707": "IVA Cobrado",
	"2010710": "ICE",
	"2010711": "IRBPNR",
	"2010708": "Ret. IVA",
	"2010709": "Ret. IR",
	"1010501": "TDS IVA",
	"1010502": "TDS IR",
}

SRI_RATE_LABELS = {"0": "0%", "6": "No Objeto", "7": "Exento", "8": "Diferenciado"}


IVA_WH_ACCOUNT_NUMBER = "2010708"
IVA_DEDUCTION_DESCRIPTION = "SRI IVA withholding"


def company_country_code(company: str | None) -> str | None:
	"""Resolve a Company country name to its ISO code, if determinable."""
	try:
		import frappe
	except ImportError:
		return None
	if not company:
		return None
	country = frappe.db.get_value("Company", company, "country")
	if not country:
		return None
	return frappe.db.get_value("Country", country, "code")


def _iva_withholding_account(company: str) -> str | None:
	"""Ledger account for IVA withholdings (bench only; None in Ring 1)."""
	try:
		import frappe
	except ImportError:
		return None
	return frappe.db.get_value(
		"Account", {"company": company, "account_number": IVA_WH_ACCOUNT_NUMBER}, "name"
	)


def validate_sustento_code(doc, method=None) -> None:
	"""Guard SRI sustento vs tipoComprobante/tpIdProv (Tabla 5)."""
	if doc.get("doctype") != "Purchase Invoice":
		return
	from l10n_ec.sri.sustentos import validate_sustento

	try:
		import frappe as _frappe
	except ImportError:
		_frappe = None  # type: ignore[assignment]

	code = (doc.get("sri_sustento_code") or "").strip() or "02"
	tp = (
		(doc.get("sri_identification_type") or "")
		or (
			_frappe.db.get_value("Supplier", doc.get("supplier"), "sri_identification_type")
			if _frappe and doc.get("supplier")
			else ""
		)
		if _frappe
		else "04"
	)
	# Derive doc_code from flags (same logic as ats_reader.classify_purchase)
	if doc.get("is_return") and doc.get("sri_is_liquidacion"):
		raise ValueError(_("A purchase cannot be a return and a liquidacion at once."))
	doc_code = (
		"04"
		if doc.get("is_return")
		else "05"
		if doc.get("sri_is_supplier_debit_note")
		else "03"
		if doc.get("sri_is_liquidacion")
		else "01"
	)
	try:
		validate_sustento(code, doc_code, tp)
	except ValueError as exc:
		if _frappe:
			_frappe.throw(str(exc))
		raise


def sync_tax_row_descriptions(doc, method=None) -> None:
	"""Make tax row descriptions follow SRI names, not account heads.

	ERPNext defaults `description = account_head` (e.g. `1010504 - IVA PAGADO...`),
	so the SRI tax is invisible. This rewrites to SRI pattern like
	`IVA 15% (4)`, `IVA 0% (0)`, `IVA Exento (7)`, `IVA No Objeto (6)`,
	`ICE 5% (3072)` for presentation only (no GL/ATS impact).
	"""
	for row in doc.get("taxes") or []:
		if (row.get("description") or "").startswith("SRI IVA withholding"):
			continue
		account_head = row.get("account_head") or ""
		number = (account_head.split(" - ")[0] or "").strip()
		label = TAX_DESCRIPTIONS.get(number)
		if not label:
			continue
		rate = row.get("rate")
		try:
			rate_val = float(rate) if rate not in (None, "") else 0.0
		except TypeError, ValueError:
			rate_val = 0.0
		if not rate_val and label in ("IVA Cobrado", "IVA Pagado"):
			# Item Tax Templates leave rate=0 (amount from item-wise details).
			# Infer SRI rate_code + tarifa for SRI naming: 0% (0), Exento (7), No Objeto (6), Diferenciado 5%/8% (8).
			try:
				import frappe as _frappe2
			except ImportError:
				_frappe2 = None  # type: ignore[assignment]
			if _frappe2 is not None:
				for item in doc.get("items") or []:
					tmpl = item.get("item_tax_template")
					if not tmpl:
						continue
					try:
						from l10n_ec.sri.tax_codes import tax_codes_for_template

						_code, rate_code = tax_codes_for_template(tmpl)
						if rate_code == "0":
							row.description = "IVA 0% (0)"
							row.rate = 0
							break
						if rate_code == "6":
							row.description = "IVA No Objeto (6)"
							row.rate = 0
							break
						if rate_code == "7":
							row.description = "IVA Exento (7)"
							row.rate = 0
							break
						tdoc = _frappe2.get_doc("Item Tax Template", tmpl)
						if tdoc.taxes:
							inferred = float(tdoc.taxes[0].tax_rate)
							row.description = f"IVA {inferred:g}% ({rate_code})"
							row.rate = inferred
							break
					except Exception:
						continue
				else:
					row.description = f"{label} {rate_val:g}%"
				continue
		row.description = f"{label} {rate_val:g}%"


def enforce_iva_deduction_row(doc, method=None, resolve_account=None, company_code=None) -> None:
	"""Ensure the automatic IVA withholding deduction row on Purchase Invoice.

	ERPNext cannot compute tax-on-tax withholdings natively, so the IVA
	withholding lives in a `Deduct` / `On Previous Row Amount` taxes row
	driven by `sri_iva_concepto`: rate comes from the caller-chosen IVA
	concepto, base is the referenced IVA row amount, and everything
	downstream (details, totals, GL, outstanding) stays native. Mixed IVA
	rates on one invoice fail loud instead of guessing. Existing rows owned
	by this automation (same account + Deduct) are updated, never doubled.
	"""
	code = company_code if company_code is not None else company_country_code(doc.get("company"))
	if not is_ecuadorian_contact(code):
		return
	concepto = (doc.get("sri_iva_concepto") or "").strip()
	if not concepto:
		return
	from l10n_ec.sri.withholding_concepts import resolve_concepto

	impuesto, rate, _description = resolve_concepto(concepto)
	if impuesto != "2":
		raise ValueError(_("IVA withholding needs an IVA concepto, got '{}'.").format(concepto))
	iva_rows = [
		row
		for row in doc.get("taxes") or []
		if not row.get("is_tax_withholding_account")
		and row.get("add_deduct_tax") != "Deduct"
		and float(row.get("tax_amount") or 0) != 0
	]
	if not iva_rows:
		raise ValueError(_("SRI IVA concepto '{}' is set but the invoice has no IVA taxes.").format(concepto))
	if len(iva_rows) > 1:
		raise ValueError(
			_("SRI IVA withholding needs exactly one IVA tax row, found {}.").format(len(iva_rows))
		)
	target = iva_rows[0]
	resolver = resolve_account or _iva_withholding_account
	account = resolver(doc.get("company"))
	if not account:
		raise ValueError(
			_("Missing IVA withholding account {} for company '{}'.").format(
				IVA_WH_ACCOUNT_NUMBER, doc.get("company")
			)
		)
	owned = [
		row
		for row in doc.get("taxes") or []
		if row.get("account_head") == account and row.get("add_deduct_tax") == "Deduct"
	]
	if owned:
		row = owned[0]
		row.rate = rate
		row.row_id = str(target.idx)
		row.description = f"{IVA_DEDUCTION_DESCRIPTION} {concepto}"
	else:
		doc.append(
			"taxes",
			{
				"charge_type": "On Previous Row Amount",
				"add_deduct_tax": "Deduct",
				"category": "Total",
				"rate": rate,
				"row_id": str(target.idx),
				"account_head": account,
				"description": f"{IVA_DEDUCTION_DESCRIPTION} {concepto}",
			},
		)
	refresh = getattr(doc, "calculate_taxes_and_totals", None)
	if callable(refresh):
		refresh()
