"""Assumed withholdings on purchases (withholding agent absorbs the tax).

When a price is agreed net with the supplier, the withholding is still
emitted (fiscal rule) but the payable stays intact: the agent books the
withheld total as non-deductible expense and keeps the SRI liability that
the native Deduct rows already posted. A compensating Journal Entry
(Dr 520230 / Cr supplier payable) posts on Purchase Invoice submit and
reverses on cancel — the `received_settlement` pattern, mirrored.
Supplier-side only; 103/104/ATS read the same boxes either way.
"""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message


#: Non-deductible expense holding assumed withholdings (renamable).
ASSUMED_EXPENSE_ACCOUNT_NUMBER = "520230"
#: SRI liability accounts whose Deduct rows the agent absorbs.
WITHHOLDING_LIABILITY_NUMBERS = frozenset({"2010708", "2010709"})


def assumed_remark(purchase_invoice: str) -> str:
	"""Idempotency marker shared by the compensation entry and its lookup.

	Deliberately NOT translated: the marker must be byte-identical in every
	locale, otherwise the lookup misses entries posted in another language
	and the compensation posts twice.
	"""
	return f"SRI-ASSUMED-WH {purchase_invoice}"


def assumed_total(tax_rows: list) -> float:
	"""Sum of native withholding Deduct rows (pure; SRI liabilities only)."""
	return round(
		sum(
			float(row.get("tax_amount") or 0.0)
			for row in tax_rows or []
			if (row.get("account_number") or "").split(" - ")[0].strip() in WITHHOLDING_LIABILITY_NUMBERS
			and row.get("add_deduct_tax") == "Deduct"
		),
		2,
	)


def assumed_lines(tax_rows: list, accounts: dict, party: dict) -> list | None:
	"""Build JE lines restoring the payable via non-deductible expense (pure).

	Only native withholding Deduct rows on SRI liability accounts count;
	everything else (IVA paid, Add rows) is ignored. ``accounts`` carries
	resolved ``expense`` / ``payable`` ledger names plus ``cost_center``;
	``party`` the linkage every line carries. Returns None when there is
	nothing to absorb.
	"""
	total = assumed_total(tax_rows)
	if not total:
		return None
	debit = {
		"account": accounts["expense"],
		"debit_in_account_currency": total,
		"cost_center": accounts["cost_center"],
		"party_type": party["party_type"],
		"party": party["party"],
	}
	credit = {
		"account": accounts["payable"],
		"credit_in_account_currency": total,
		"cost_center": accounts["cost_center"],
		"party_type": party["party_type"],
		"party": party["party"],
	}
	return [debit, credit]


def _resolve_accounts(company: str) -> dict:
	"""Ledger names for the compensation entry (bench only)."""
	if frappe is None:  # pragma: no cover
		return {}
	expense = frappe.db.get_value(
		"Account", {"company": company, "account_number": ASSUMED_EXPENSE_ACCOUNT_NUMBER}, "name"
	)
	if not expense:
		raise ValueError(
			_("Missing account {} for assumed withholdings.").format(ASSUMED_EXPENSE_ACCOUNT_NUMBER)
		)
	return {
		"expense": expense,
		"cost_center": frappe.db.get_value("Company", company, "cost_center"),
	}


def _existing_entry(purchase_invoice: str):
	"""Submitted compensation JE for an invoice, if any (idempotency)."""
	if frappe is None:  # pragma: no cover
		return None
	name = frappe.db.get_value(
		"Journal Entry", {"user_remark": assumed_remark(purchase_invoice), "docstatus": 1}, "name"
	)
	return frappe.get_doc("Journal Entry", name) if name else None


def settle_assumed_withholding(doc, method=None) -> None:
	"""Post the compensation entry for assumed withholdings on submit."""
	if frappe is None:  # pragma: no cover
		return
	if not doc.get("sri_assumed_withholding"):
		return
	if _existing_entry(doc.get("name")) is not None:
		return
	rows = [
		{
			"account_number": (row.get("account_head") or "").split(" - ")[0].strip(),
			"tax_amount": row.get("tax_amount"),
			"add_deduct_tax": row.get("add_deduct_tax"),
		}
		for row in doc.get("taxes") or []
	]
	lines = assumed_lines(
		rows,
		{
			**_resolve_accounts(doc.get("company")),
			"payable": doc.get("credit_to"),
		},
		{"party_type": "Supplier", "party": doc.get("supplier")},
	)
	if lines is None:
		return
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": doc.get("company"),
			"posting_date": doc.get("posting_date"),
			"user_remark": assumed_remark(doc.get("name")),
			"accounts": lines,
		}
	)
	je.insert(ignore_permissions=True)
	je.submit()


def cancel_assumed_withholding(doc, method=None) -> None:
	"""Cancel the compensation entry when the invoice is cancelled."""
	if frappe is None:  # pragma: no cover
		return
	if not doc.get("sri_assumed_withholding"):
		return
	je = _existing_entry(doc.get("name"))
	if je is not None:
		je.cancel()
