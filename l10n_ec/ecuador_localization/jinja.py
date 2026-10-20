"""Jinja helpers exposed to print formats (see `jinja` in `hooks.py`)."""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

from l10n_ec.sri.barcode import access_key_barcode_data_uri


def sri_barcode(access_key: str) -> str:
	"""Render an access key as a data-URI PNG (pure, Ring-1 testable)."""
	return access_key_barcode_data_uri(access_key)


def sri_authorized_voucher(reference_doctype: str, reference_name: str) -> dict | None:
	"""Latest authorized voucher data for an invoice, or None when absent."""
	if frappe is None:
		return None
	rows = frappe.get_all(
		"SRI Electronic Voucher",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"voucher_state": "Authorized",
		},
		fields=["access_key", "authorization_number", "authorization_date"],
		order_by="modified desc",
		limit=1,
	)
	return rows[0] if rows else None


def sri_emisor(company_name: str) -> dict | None:
	"""Emisor identity for print formats, or None when unavailable."""
	if frappe is None:
		return None
	company = frappe.db.get_value(
		"Company", company_name, ["company_name", "tax_id"], as_dict=True
	)
	if not company or not company.tax_id:
		return None
	return {"legal_name": company.company_name, "ruc": company.tax_id}
