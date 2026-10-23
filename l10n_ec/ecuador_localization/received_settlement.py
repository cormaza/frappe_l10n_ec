"""Settlement of customer-withheld taxes (sales-side received withholdings).

Ecuadorian customers acting as withholding agents pay the invoice net of
IR/IVA withholdings and issue their own Comprobante de Retencion. ERPNext
books the invoice gross, so this module settles the withheld remainder with
a Journal Entry (Dr TDS-credit assets / Cr receivable against the invoice):
IR rows come from the invoice native entries, the IVA row synthesizes from
the invoice IVA taxes through the caller-chosen concepto. Purchase-side
emission (`voucher_flow`) is untouched.
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


IR_CREDIT_ACCOUNT_NUMBER = "1010502"
IVA_CREDIT_ACCOUNT_NUMBER = "1010501"


def settlement_values(sales_invoice: str) -> dict | None:
	"""Received-withholding values from the settlement JE, if posted."""
	if frappe is None:  # pragma: no cover
		return None
	je_name = frappe.db.get_value(
		"Journal Entry",
		{"user_remark": settlement_remark(sales_invoice), "docstatus": 1},
		"name",
	)
	if not je_name:
		return None
	je = frappe.get_doc("Journal Entry", je_name)
	values = {"iva_value": 0.0, "renta_value": 0.0}
	for line in je.get("accounts") or []:
		account = line.get("account") or ""
		if "1010501" in account:
			values["iva_value"] += float(line.get("debit_in_account_currency") or 0)
		elif "1010502" in account:
			values["renta_value"] += float(line.get("debit_in_account_currency") or 0)
	return values


def settlement_remark(sales_invoice: str) -> str:
	"""Idempotency marker shared by the settlement entry and its lookup."""
	return _("SRI received withholdings {}").format(sales_invoice)


def settlement_lines(ir_amount: float, iva_amount: float, accounts: dict, party: dict) -> list | None:
	"""Build JE account lines from resolved amounts (pure; None when empty).

	Journal Entry lines carry no invoice linkage (the doctype has no
	against_voucher fields): matching to the invoice happens in Payment
	Reconciliation. `ir_amount`/`iva_amount` are the computed totals (0 means
	none), `accounts` the resolved `ir_asset` / `iva_asset` / `receivable`
	ledger names plus `cost_center`, `party` the `party_type` / `party`
	linkage every line carries.
	"""
	lines = []
	if round(float(ir_amount), 2):
		lines.append(
			{
				"account": accounts["ir_asset"],
				"debit_in_account_currency": round(float(ir_amount), 2),
				"cost_center": accounts["cost_center"],
				"party_type": party["party_type"],
				"party": party["party"],
			}
		)
	if round(float(iva_amount), 2):
		lines.append(
			{
				"account": accounts["iva_asset"],
				"debit_in_account_currency": round(float(iva_amount), 2),
				"cost_center": accounts["cost_center"],
				"party_type": party["party_type"],
				"party": party["party"],
			}
		)
	if not lines:
		return None
	total = round(sum(line["debit_in_account_currency"] for line in lines), 2)
	credit: dict = {
		"account": accounts["receivable"],
		"credit_in_account_currency": total,
		"cost_center": accounts["cost_center"],
		"party_type": party["party_type"],
		"party": party["party"],
	}
	lines.append(credit)
	return lines


def _asset_account(company: str, number: str) -> str | None:
	"""Ledger account name by number (bench only; None in Ring 1)."""
	if frappe is None:
		return None
	return frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")


def _default_cost_center(company: str) -> str | None:
	"""Company default cost center (bench only; None in Ring 1)."""
	if frappe is None:
		return None
	return frappe.db.get_value("Company", company, "cost_center")


def build_settlement_for_si(si_doc, resolve_asset=None, cost_center_resolver=None) -> dict | None:
	"""Settle a Sales Invoice received withholdings into a JE dict (or None).

	Both legs derive from invoice data, never native withholding entries:
	IR from the net total through `sri_ir_concepto`, IVA from the IVA line
	taxes through `sri_iva_concepto`. Empty conceptos mean no leg.
	"""
	from l10n_ec.ecuador_localization.voucher_flow import base_lines, map_line_taxes, synthesize_iva_row
	from l10n_ec.sri.withholding_concepts import resolve_concepto

	party = {"party_type": "Customer", "party": si_doc.get("customer")}
	resolver = resolve_asset or _asset_account
	company = si_doc.get("company")
	ir_amount = 0.0
	ir_concepto = (si_doc.get("sri_ir_concepto") or "").strip()
	if ir_concepto:
		impuesto, rate, _description = resolve_concepto(ir_concepto)
		if impuesto != "1":
			raise ValueError(_("IR withholding needs an IR concepto, got '{}'.").format(ir_concepto))
		ir_amount = round(float(si_doc.get("net_total") or 0) * rate / 100, 2)
	iva_amount = 0.0
	iva_concepto = (si_doc.get("sri_iva_concepto") or "").strip()
	if iva_concepto:
		mapped = [map_line_taxes(line) for line in base_lines(si_doc)]
		synthesized = synthesize_iva_row(mapped, iva_concepto)
		if synthesized is not None:
			iva_amount = synthesized["amount"]
	return _settlement_je(si_doc, ir_amount, iva_amount, resolver, cost_center_resolver, party)


def _settlement_je(si_doc, ir_amount, iva_amount, resolver, cost_center_resolver, party) -> dict | None:
	"""Assemble the settlement JE dict from resolved amounts (shared core)."""
	company = si_doc.get("company")
	accounts = {
		"ir_asset": resolver(company, IR_CREDIT_ACCOUNT_NUMBER),
		"iva_asset": resolver(company, IVA_CREDIT_ACCOUNT_NUMBER),
		"receivable": si_doc.get("debit_to"),
		"cost_center": (cost_center_resolver or _default_cost_center)(company),
	}
	if not accounts["receivable"]:
		return None
	lines = settlement_lines(ir_amount, iva_amount, {k: (v or "") for k, v in accounts.items()}, party)
	if lines is None:
		return None
	if (ir_amount and not accounts["ir_asset"]) or (iva_amount and not accounts["iva_asset"]):
		raise ValueError(_("Missing TDS credit accounts for company '{}'.").format(company))
	return {
		"company": company,
		"posting_date": si_doc.get("posting_date"),
		"user_remark": settlement_remark(si_doc.get("name")),
		"accounts": lines,
	}


def build_settlement_for_allocation(si_name: str, ir_value, iva_value) -> dict | None:
	"""Settle one batch allocation with its agreed (capped) amounts.

	Customer-side: unlike `build_settlement_for_si` (which recomputes from
	the invoice conceptos), the slip amounts were agreed with the customer
	and validated by `received_batch`; they are booked as stated.
	"""
	if frappe is None:  # pragma: no cover
		return None
	si_doc = frappe.get_doc("Sales Invoice", si_name)
	party = {"party_type": "Customer", "party": si_doc.get("customer")}
	return _settlement_je(
		si_doc,
		round(float(ir_value or 0.0), 2),
		round(float(iva_value or 0.0), 2),
		_asset_account,
		None,
		party,
	)


def _existing_settlement(sales_invoice: str):
	"""Submitted settlement JE for an invoice, if any (idempotency)."""
	if frappe is None:  # pragma: no cover
		return None
	name = frappe.db.get_value(
		"Journal Entry",
		{"user_remark": settlement_remark(sales_invoice), "docstatus": 1},
		"name",
	)
	return frappe.get_doc("Journal Entry", name) if name else None


def settle_received_withholdings(doc, method=None) -> None:
	"""Create settlement entries for received withholdings on payment receipt."""
	if frappe is None:  # pragma: no cover
		return
	if doc.get("payment_type") != "Receive" or doc.get("party_type") != "Customer":
		return
	linked = doc.get("sri_received_withholding")
	if linked and frappe.db.exists("SRI Received Withholding", linked):
		settle_batch_withholdings(linked)
		return
	for reference in doc.get("references") or []:
		if reference.get("reference_doctype") != "Sales Invoice":
			continue
		si_name = reference.get("reference_name")
		if not si_name or _existing_settlement(si_name):
			continue
		si_doc = frappe.get_doc("Sales Invoice", si_name)
		settlement = build_settlement_for_si(si_doc)
		if settlement is None:
			continue
		je = frappe.get_doc({"doctype": "Journal Entry", **settlement})
		je.insert(ignore_permissions=True)
		je.submit()
		# Outstanding display refreshes in Payment Reconciliation (standard
		# tool for adjustment entries); the books balance at submit.


def stamp_slip_references(batch_name: str, stamp: bool) -> None:
	"""Write (or clear) the shared slip refs onto allocated invoices.

	Downstream readers (ATS, 104 received refs) keep working unchanged:
	they read the SI fields this stamps. Clearing only blanks refs that
	still point at this slip; a posted settlement JE blocks unclearing.
	"""
	if frappe is None:  # pragma: no cover
		return
	batch = frappe.get_doc("SRI Received Withholding", batch_name)
	refs = {
		"sri_received_retencion_number": batch.get("retencion_number") or "",
		"sri_received_retencion_auth": batch.get("authorization") or "",
		"sri_received_retencion_date": batch.get("retencion_date"),
		"sri_received_retencion_key": batch.get("access_key") or "",
	}
	for row in batch.get("allocations") or []:
		si_name = row.get("sales_invoice")
		if not si_name or not frappe.db.exists("Sales Invoice", si_name):
			continue
		if stamp:
			for field, value in refs.items():
				if value:
					frappe.db.set_value("Sales Invoice", si_name, field, value)
		else:
			if _existing_settlement(si_name) is not None:
				raise ValueError(_("Invoice '{}' already settled; its slip references stay.").format(si_name))
			current = frappe.db.get_value("Sales Invoice", si_name, "sri_received_retencion_number")
			if current == refs["sri_received_retencion_number"]:
				for field in refs:
					frappe.db.set_value("Sales Invoice", si_name, field, None)


def settle_batch_withholdings(batch_name: str) -> list:
	"""Post one settlement JE per allocation of a received batch."""
	if frappe is None:  # pragma: no cover
		return []
	batch = frappe.get_doc("SRI Received Withholding", batch_name)
	posted = []
	for row in batch.get("allocations") or []:
		si_name = row.get("sales_invoice")
		if not si_name or _existing_settlement(si_name) is not None:
			continue
		settlement = build_settlement_for_allocation(si_name, row.get("ir_value"), row.get("iva_value"))
		if settlement is None:
			continue
		je = frappe.get_doc({"doctype": "Journal Entry", **settlement})
		je.insert(ignore_permissions=True)
		je.submit()
		posted.append(je.name)
	return posted


def cancel_received_settlements(doc, method=None) -> None:
	"""Cancel settlement entries when the receipt is cancelled."""
	if frappe is None:  # pragma: no cover
		return
	if doc.get("payment_type") != "Receive" or doc.get("party_type") != "Customer":
		return
	for reference in doc.get("references") or []:
		if reference.get("reference_doctype") != "Sales Invoice":
			continue
		je = _existing_settlement(reference.get("reference_name"))
		if je is not None:
			je.cancel()
