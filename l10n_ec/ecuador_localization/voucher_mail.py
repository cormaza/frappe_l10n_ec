"""Authorized-voucher customer email (roadmap Phase 6C).

Pure composition (`resolve_recipients`, `authorized_mail_subject`,
`build_attachments`) stays testable in Ring 1. Rendering uses the standard
`download_pdf` path (whatever engine the site configures); delivery goes
through the Email Queue, so no SMTP server is needed to prove it.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]


def resolve_recipients(customer_email: str | None, contact_email: str | None) -> list:
	"""Prefer the customer email, fall back to the primary contact email."""
	for candidate in (customer_email, contact_email):
		if (candidate or "").strip():
			return [candidate.strip()]
	return []


def authorized_mail_subject(access_key: str) -> str:
	"""Email subject for an authorized voucher."""
	return _("Authorized electronic voucher {}").format(access_key)


def build_attachments(xml_file_id: str) -> list:
	"""Queue-ready attachments: the signed XML file plus the on-demand RIDE PDF."""
	return [{"fid": xml_file_id}]


def _customer_contact_email(customer: str) -> str | None:
	contact = frappe.db.get_value(
		"Contact",
		{"link_doctype": "Customer", "link_name": customer, "is_primary_contact": 1},
		"email_id",
	)
	return contact


def send_authorized_voucher_mail(voucher_name: str):
	"""Queue the authorized-voucher email with XML+PDF; None when skipped."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to send voucher mail.")
	from l10n_ec.ecuador_localization.voucher_flow import read_voucher_xml

	voucher = frappe.get_doc("SRI Electronic Voucher", voucher_name)
	if voucher.voucher_state != "Authorized":
		return None
	customer = frappe.db.get_value(voucher.reference_doctype, voucher.reference_name, "customer")
	recipients = []
	if customer:
		recipients = resolve_recipients(
			frappe.db.get_value("Customer", customer, "email_id"),
			_customer_contact_email(customer),
		)
	if not recipients:
		return None
	xml_file_id = frappe.db.get_value("File", {"file_url": voucher.signed_xml}, "name")
	if not xml_file_id:
		return None
	return frappe.sendmail(
		recipients=recipients,
		subject=authorized_mail_subject(voucher.access_key),
		message=_("Your electronic voucher was authorized by the SRI."),
		attachments=build_attachments(xml_file_id)
		+ [
				{
					"print_format_attachment": 1,
					"doctype": voucher.reference_doctype,
					"name": voucher.reference_name,
					"print_format": "SRI RIDE",
				}
			],
		reference_doctype="SRI Electronic Voucher",
		reference_name=voucher_name,
	)
