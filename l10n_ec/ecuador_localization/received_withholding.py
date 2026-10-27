"""Bench glue for received customer withholdings (07 where we are the subject).

Shares the T4 pure core (:mod:`l10n_ec.sri.received_retention`); this
module only touches the database: resolve the customer, auto-match
submitted sales invoices through their authorized vouchers, guard
duplicates, and insert the SRI Received Withholding batch as a draft.
Downstream (stamp, settlement, 103/104) is untouched existing flow.
"""

try:
	import frappe
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message

	frappe = None  # type: ignore[assignment]

from l10n_ec.sri.received_retention import map_received_retencion
from l10n_ec.sri.voucher_data import parse_emitted_xml


def _resolve_customer(tax_id: str, customer_name: str) -> str:
	"""Customer name for an emisor RUC; fail loud asking to create it first."""
	name = frappe.db.get_value("Customer", {"tax_id": tax_id}, "name")
	if name:
		return name
	raise ValueError(
		_("Customer with RUC '{}' ({}) does not exist: create it first, then import the XML again.").format(
			tax_id, customer_name or "?"
		)
	)


def _match_sales_invoice(customer: str, doc_number: str) -> str | None:
	"""Submitted Sales Invoice behind an authorized voucher number, or None.

	Matches through the authorized SRI Electronic Voucher (the SRI number
	is the voucher's, not the ERPNext doc name) and confirms the invoice
	belongs to the same customer. Ambiguity or mismatch resolves to
	manual allocation, never to a guess.
	"""
	names = frappe.db.get_all(
		"SRI Electronic Voucher",
		filters={
			"sri_number": doc_number,
			"voucher_state": "Authorized",
			"reference_doctype": "Sales Invoice",
		},
		pluck="reference_name",
	)
	candidates = []
	for si_name in dict.fromkeys(names or []):
		if not frappe.db.exists("Sales Invoice", si_name):
			continue
		if frappe.db.get_value("Sales Invoice", si_name, "customer") != customer:
			continue
		candidates.append(si_name)
	if len(candidates) == 1:
		return candidates[0]
	return None


def _create_draft_batch(xml_text: str, company: str) -> str:
	"""Shared core: authorized-XML-or-uploaded file to a draft batch."""
	parsed = parse_emitted_xml(xml_text)
	if (parsed or {}).get("kind") != "retencion":
		frappe.throw(
			_("Only customer withholding slips (07) can be imported here (got '{}').").format(
				parsed.get("kind")
			)
		)
		raise ValueError("unreachable")
	try:
		mapped = map_received_retencion(parsed)
	except ValueError as exc:
		frappe.throw(str(exc))
		raise
	try:
		customer = _resolve_customer(mapped["customer_tax_id"], mapped.get("customer_name", ""))
	except ValueError as exc:
		frappe.throw(str(exc))
		raise
	duplicate = frappe.db.get_value(
		"SRI Received Withholding",
		{"customer": customer, "retencion_number": mapped["retencion_number"]},
		"name",
	)
	if duplicate:
		frappe.throw(
			_("Customer withholding '{}' was already imported as {}.").format(
				mapped["retencion_number"], duplicate
			)
		)
		raise ValueError("unreachable")
	allocations = []
	unmatched = []
	for alloc in mapped["allocations"]:
		si_name = _match_sales_invoice(customer, alloc["doc_number"])
		if si_name is None:
			unmatched.append(alloc["doc_number"])
			continue
		allocations.append(
			{"sales_invoice": si_name, "ir_value": alloc["ir_value"], "iva_value": alloc["iva_value"]}
		)
	if unmatched:
		frappe.throw(
			_(
				"Could not match sustento {} to a submitted, authorized Sales Invoice of '{}': "
				"authorize the sale or allocate it manually after import."
			).format(", ".join(unmatched), customer)
		)
		raise ValueError("unreachable")
	if not allocations:
		frappe.throw(_("The withholding carries no allocatable sustento documents."))
		raise ValueError("unreachable")
	doc = frappe.get_doc(
		{
			"doctype": "SRI Received Withholding",
			"company": company,
			"customer": customer,
			"retencion_number": mapped["retencion_number"],
			"authorization": mapped["authorization"],
			"retencion_date": mapped["retencion_date"],
			"access_key": mapped["authorization"],
			"allocations": allocations,
		}
	)
	doc.insert()
	return doc.name


@frappe.whitelist() if frappe else (lambda fn: fn)
def import_customer_withholding(xml_text: str, company: str) -> str:
	"""Create a draft SRI Received Withholding batch from an uploaded 07 XML.

	File upload path: the XML can be as old as the customer email it came
	in. See the SRI fetch for the online alternative.
	"""
	if frappe is None:  # pragma: no cover
		raise ValueError("Withholding import needs a Frappe Bench.")
	if not company:
		frappe.throw(_("A company is required to file the received withholding."))
		raise ValueError("unreachable")
	return _create_draft_batch(xml_text, company)
