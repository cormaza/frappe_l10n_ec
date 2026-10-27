"""Contact tax identification hook contract for Customer/Supplier validation.

Phase 3 wiring calls :func:`validate_contact_tax_id` from the `validate` hook
and converts the `ValueError` into `frappe.throw`. Gating uses the Country
ISO code (`EC`), resolved from the contact address by the caller, so this
module stays free of `frappe` imports and testable in Ring 1.
"""

from l10n_ec.sri.codes import sri_code
from l10n_ec.sri.identification import (
	FINAL_CONSUMER_ID,
	validate_identification,
	validate_identification_with_fallback,
)

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


def classify_country(country_code: str | None) -> str:
	"""Tri-state fiscal nationality: ``EC``, ``foreign`` or ``unknown``.

	Doctrine: restrictions trigger only on proven ``EC``; ``unknown`` (no
	country resolvable from the record) never restricts and is never
	foreign. Affirmative SRI acts (emission) refuse proven ``foreign`` and
	let ``unknown`` through for SRI itself to judge.
	"""
	code = (country_code or "").strip().upper()
	if code == ECUADOR_COUNTRY_CODE:
		return "EC"
	if code:
		return "foreign"
	return "unknown"


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


#: Days an SRI-confirmed RUC stays cached (registry data is stable).
SRI_LOOKUP_CACHE_DAYS = 7


def validate_contact_tax_id_with_fallback(
	country_code: str | None,
	identification_type_code: str | None,
	tax_id: str | None,
	fetch=None,
	cache=None,
) -> str:
	"""Validate a contact tax ID with the SRI registry as soft fallback.

	Returns the path taken: ``skipped`` (non-EC), ``stdnum`` (checksum),
	or ``sri`` (registry knows it). Raises `ValueError` on rejection or
	unverifiable registry answers, with the cause and the override hint.
	``fetch``/``cache`` are injectable (Ring-1 tests); bench passes the
	default network fetch plus ``frappe.cache`` (positives only).
	"""
	if not is_ecuadorian_contact(country_code):
		return "skipped"
	type_code = (identification_type_code or "").strip()
	cleaned = (tax_id or "").strip()
	if validate_identification(type_code, cleaned):
		return "stdnum"
	if type_code != "04" or not cleaned:
		raise ValueError(_("Invalid tax identification '{}' for type '{}'.").format(cleaned, type_code))
	cache_key = f"sri-ruc:{cleaned}"
	if cache is not None:
		try:
			if cache.get(cache_key) == "sri":
				return "sri"
		except Exception:
			pass
	ok, path = validate_identification_with_fallback(type_code, cleaned, fetch=fetch)
	if ok:
		if cache is not None:
			try:
				cache.set(cache_key, "sri", expires_in_days=SRI_LOOKUP_CACHE_DAYS)
			except Exception:
				pass
		return path
	if path == "unverifiable":
		raise ValueError(
			_(
				"Tax identification '{}' failed the checksum and the SRI registry "
				"could not be reached to confirm it; check the connection or set "
				"'Skip SRI ID Validation' on the contact with the number verified "
				"at the SRI portal."
			).format(cleaned)
		)
	raise ValueError(_("Invalid tax identification '{}' for type '{}'.").format(cleaned, type_code))


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


def validate_factura_cf_total(
	identification_type_code: str | None,
	tax_id: str | None,
	total: float | None,
	threshold: float = FINAL_CONSUMER_THRESHOLD,
) -> None:
	"""Reject a single factura voucher to generic CF over the threshold.

	SRI authorizes no factura above the threshold without buyer
	identification: one voucher carrying the whole amount is stillborn, so
	it fails here instead of travelling to SRI. Consolidated invoices
	emit per ticket (each voucher carries its own ticket total).
	"""
	if not is_generic_final_consumer(identification_type_code, tax_id):
		return
	if (total or 0) > threshold:
		raise ValueError(
			_(
				"Factura to Consumidor Final above {} needs buyer identification; a single voucher cannot carry it."
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
	"""Guard SRI sustento vs tipoComprobante (Tabla 5 cross-table)."""
	if doc.get("doctype") != "Purchase Invoice":
		return
	from l10n_ec.sri.reimbursement import validate_sustento_for_doc

	try:
		import frappe as _frappe
	except ImportError:
		_frappe = None  # type: ignore[assignment]

	code = sri_code(doc.get("sri_sustento_code")) or "02"
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
	# Derive doc_code from flags (same logic as ats_reader.classify_purchase + 41).
	if doc.get("is_return") and doc.get("sri_is_liquidacion"):
		raise ValueError(_("A purchase cannot be a return and a liquidacion at once."))
	if doc.get("sri_is_reimbursement"):
		doc_code = "41"
	else:
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
		validate_sustento_for_doc(code, doc_code, tp or "04")
	except ValueError as exc:
		if _frappe:
			_frappe.throw(str(exc))
		raise


def _supplier_country(_frappe, supplier: str | None) -> str | None:
	"""Supplier country: master record first, default billing address next."""
	if not supplier:
		return None
	country = _frappe.db.get_value("Supplier", supplier, "country")
	if country:
		return country
	from frappe.contacts.doctype.address.address import get_default_address

	address = get_default_address("Supplier", supplier)
	if not address:
		return None
	return _frappe.db.get_value("Address", address, "country")


def validate_no_local_vat_on_exterior_purchase(doc, method=None) -> None:
	"""Forbid Ecuadorian VAT templates on exterior purchase invoices.

	A foreign supplier never charges local VAT: the import VAT credit is
	born by the DAI liquidation (SRI Import Settlement, LRTI Art. 59),
	never by the supplier invoice. Unknown country never restricts.
	"""
	if doc.get("doctype") != "Purchase Invoice":
		return
	templates = sorted(
		{row.get("item_tax_template") for row in (doc.get("items") or []) if row.get("item_tax_template")}
	)
	if not templates:
		return
	try:
		import frappe as _frappe
	except ImportError:
		return
	from l10n_ec.sri.import_settlement import validate_no_local_vat

	try:
		validate_no_local_vat(_supplier_country(_frappe, doc.get("supplier")), templates)
	except ValueError as exc:
		_frappe.throw(str(exc))
		raise


#: Withholding labels whose native rate column arrives 0 with the amount set.
WITHHOLDING_LABELS = frozenset({"Ret. IR", "Ret. IVA", "TDS IVA", "TDS IR"})


def _category_withholding_rate(category: str | None, resolve_category_rate=None) -> float | None:
	"""Single rate from a Tax Withholding Category, or None when ambiguous.

	`resolve_category_rate` maps a category name to its single rate (bench
	default reads the category's rates table); anything but exactly one
	rate is ambiguity, never a guess.
	"""
	if not category:
		return None
	if resolve_category_rate is not None:
		return resolve_category_rate(category)
	try:
		import frappe as _frappe3
	except ImportError:  # pragma: no cover
		return None
	rates = _frappe3.get_all(
		"Tax Withholding Rate", filters={"parent": category}, pluck="tax_withholding_rate"
	)
	if len(rates) != 1:
		return None
	return float(rates[0])


def validate_reimbursement_details(doc, method=None) -> None:
	"""Guard reimbursement lines and totbasesImpReemb (calculated, opt-in override)."""
	if doc.get("doctype") not in ("Purchase Invoice", "Sales Invoice"):
		return
	from l10n_ec.sri.reimbursement import resolve_reimbursement_total

	try:
		import frappe as _frappe
	except ImportError:
		_frappe = None  # type: ignore[assignment]

	lines = doc.get("sri_reimbursement_details") or []
	if not doc.get("sri_is_reimbursement") and not lines:
		return
	if doc.get("sri_is_reimbursement") and not lines:
		msg = _("Reimbursement invoice needs at least one reimbursement detail.")
		if _frappe:
			_frappe.throw(msg)
		raise ValueError(msg)
	override = doc.get("sri_reimbursement_override_value")
	allow = bool(doc.get("sri_allow_reimbursement_override"))
	try:
		total = resolve_reimbursement_total(
			[{"base_amount": line.get("base_amount", 0.0)} for line in lines],
			override,
			allow,
		)
	except ValueError as exc:
		if _frappe:
			_frappe.throw(str(exc))
		raise
	if _frappe is None:
		try:
			doc["sri_reimbursement_total"] = total
		except Exception:
			pass


def sync_tax_row_descriptions(doc, method=None, resolve_category_rate=None, company_code=None) -> None:
	"""Make tax row descriptions follow SRI names, not account heads.

	ERPNext defaults `description = account_head` (e.g. `1010504 - IVA PAGADO...`),
	so the SRI tax is invisible. This rewrites to SRI pattern like
	`IVA 15% (4)`, `IVA 0% (0)`, `IVA Exento (7)`, `IVA No Objeto (6)`,
	`ICE 5% (3072)` for presentation only (no GL/ATS impact). Proven
	non-EC companies keep their native descriptions (tri-state doctrine).
	"""
	code = company_code if company_code is not None else company_country_code(doc.get("company"))
	if classify_country(code) != "EC":
		return
	category_rate = _category_withholding_rate(doc.get("tax_withholding_category"), resolve_category_rate)
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
		if not rate_val and label in WITHHOLDING_LABELS and row.get("tax_amount"):
			fallback = category_rate
			if fallback:
				row.description = f"{label} {fallback:g}%"
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
	concepto = sri_code(doc.get("sri_iva_concepto"))
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
