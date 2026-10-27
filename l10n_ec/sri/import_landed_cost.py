"""SRI import landed cost mapping (pure Python, no frappe).

T4 scope: the decision layer between a settled import and ERPNext's
native Landed Cost Voucher. Selecting which receipt the LCV attaches to
and shaping the cost legs into LCV tax rows is pure and tested; creating
and submitting the LCV document itself belongs to the controller (bench).
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


def select_receipt_document(
	purchase_receipt: str | None,
	purchase_invoice: str | None,
	invoice_has_update_stock: bool = False,
) -> tuple | None:
	"""Pick the receipt the LCV attaches to, or ``None`` when impossible.

	A Purchase Receipt always qualifies; a Purchase Invoice only with
	``Update Stock`` checked (native LCV rule). A bare Purchase Order
	never qualifies: goods must be received before recosting.
	"""
	if purchase_receipt:
		return ("Purchase Receipt", purchase_receipt)
	if purchase_invoice and invoice_has_update_stock:
		return ("Purchase Invoice", purchase_invoice)
	return None


def _tax_row(leg: dict, label: str) -> dict:
	amount = leg.get("amount")
	if amount is None:
		raise ValueError(_("LCV leg '{}' needs an amount.").format(leg.get("source")))
	amount = float(amount)
	if amount < 0:
		raise ValueError(_("LCV leg '{}' amount cannot be negative (got '{}').").format(leg.get("source"), amount))
	if amount == 0:
		return {}
	expense_account = (leg.get("expense_account") or "").strip()
	if not expense_account:
		raise ValueError(_("LCV leg '{}' needs an expense account on its invoice.").format(leg.get("source")))
	return {
		"description": f"{label} ({leg.get('source')})",
		"amount": amount,
		"expense_account": expense_account,
		"account_currency": leg.get("account_currency") or "USD",
		"exchange_rate": float(leg.get("exchange_rate") or 1.0),
	}


def build_lcv_taxes(freight: dict | None, insurance: dict | None) -> list:
	"""Shape freight/insurance legs into native LCV tax rows.

	Zero legs are skipped (nothing to distribute); when nothing remains,
	fail loud instead of submitting an empty LCV.
	"""
	rows = [
		row
		for row in (
			_tax_row(freight or {}, "Freight"),
			_tax_row(insurance or {}, "Insurance"),
		)
		if row
	]
	if not rows:
		raise ValueError(_("LCV needs at least one nonzero cost leg (freight/insurance)."))
	return rows
