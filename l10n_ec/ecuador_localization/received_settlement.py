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
	accounts = {
		"ir_asset": resolver(company, IR_CREDIT_ACCOUNT_NUMBER),
		"iva_asset": resolver(company, IVA_CREDIT_ACCOUNT_NUMBER),
		"receivable": si_doc.get("debit_to"),
		"cost_center": (cost_center_resolver or _default_cost_center)(company),
	}
	if not accounts["receivable"]:
		return None
	lines = settlement_lines(
		ir_amount, iva_amount, {k: (v or "") for k, v in accounts.items()}, party
	)
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
