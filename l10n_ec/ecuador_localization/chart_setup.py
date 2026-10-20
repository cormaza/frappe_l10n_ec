"""Ecuador NIIF chart installation for new companies (roadmap Phase 4).

ERPNext's chart picker only reads its own template folders, so this app
ships its verified tree and installs it through ERPNext's `create_charts`
with a custom chart. Auto-install fires only for Ecuadorian companies
that still have zero accounts; it never replaces existing charts.
"""

import json
from pathlib import Path

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

CHART_PATH = Path(__file__).parent / "chart_of_accounts" / "ec_niif_chart_template.json"

RECEIVABLE_ACCOUNT_NUMBER = "101020503"
PAYABLE_ACCOUNT_NUMBER = "2010301"

try:
	from l10n_ec.ecuador_localization.tax_templates import setup_ecuadorian_taxes
except ImportError:  # pragma: no cover
	setup_ecuadorian_taxes = None  # type: ignore[assignment]


def get_ec_chart_tree() -> dict:
	"""Load the Ecuador NIIF chart tree shipped with this app."""
	return json.loads(CHART_PATH.read_text(encoding="utf-8"))["tree"]


def find_account_path(tree: dict, account_number: str, path=()) -> tuple | None:
	"""Return the name path to an account number, or None when absent."""
	for name, child in tree.items():
		if name in ("account_number", "root_type", "account_type"):
			continue
		if child.get("account_number") == account_number:
			return (*path, name)
		found = find_account_path(child, account_number, (*path, name))
		if found is not None:
			return found
	return None


def install_ecuadorian_chart(company: str) -> None:
	"""Install the NIIF chart into a company that has no accounts yet."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to install the chart of accounts.")
	try:
		from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
			create_charts,
		)
	except ImportError as exc:
		raise RuntimeError("erpnext is required to install the chart of accounts.") from exc
	if frappe.db.count("Account", {"company": company}):
		return
	create_charts(company, custom_chart=get_ec_chart_tree())
	_set_company_default_accounts(company)


def _set_company_default_accounts(company: str) -> None:
	"""Point Company control accounts at the NIIF trade control leaves."""
	for number, fieldname in (
		(RECEIVABLE_ACCOUNT_NUMBER, "default_receivable_account"),
		(PAYABLE_ACCOUNT_NUMBER, "default_payable_account"),
	):
		account = frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")
		if account:
			frappe.db.set_value("Company", company, fieldname, account)


def setup_company_chart(doc, method=None) -> None:
	"""Company `after_insert` hook: install the NIIF chart when applicable."""
	if frappe is None:
		return
	if (frappe.db.get_value("Country", doc.get("country"), "code") or "").upper() != "EC":
		return
	if frappe.db.count("Account", {"company": doc.name}):
		return
	install_ecuadorian_chart(doc.name)
	if setup_ecuadorian_taxes is not None:
		setup_ecuadorian_taxes(doc.name)


@frappe.whitelist() if frappe else (lambda f: f)
def reinstall_ecuadorian_chart(company: str) -> None:
	"""Replace a company's accounts with the NIIF chart; blocked by GL entries."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to reinstall the chart of accounts.")
	if frappe.db.count("GL Entry", {"company": company}):
		frappe.throw(frappe._("Cannot reinstall the chart: the company already has ledger entries."))
	for df in frappe.get_meta("Company").fields:
		if df.fieldtype == "Link" and df.options == "Account":
			frappe.db.set_value("Company", company, df.fieldname, None)
	for title in frappe.get_all("Item Tax Template", filters={"company": company}, pluck="name"):
		frappe.delete_doc("Item Tax Template", title, ignore_permissions=True)
	for name in frappe.get_all("Account", filters={"company": company}, pluck="name", order_by="lft desc"):
		frappe.delete_doc("Account", name, ignore_permissions=True)
	install_ecuadorian_chart(company)
	if setup_ecuadorian_taxes is not None:
		setup_ecuadorian_taxes(company)
