"""Authorized-voucher customer email (roadmap Phase 6C).

Pure composition (`resolve_recipients`, `authorized_mail_subject`,
`ride_print_format`, `build_attachments`) stays testable in Ring 1.
Rendering uses the standard `download_pdf` path (whatever engine the site
configures); delivery goes through the Email Queue, so no SMTP server is
needed to prove it.
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


RIDE_PRINT_FORMATS = {
	"01": "SRI RIDE",
	"06": "SRI RIDE Delivery Note",
	"07": "SRI RIDE Withholding",
}


def ride_print_format(cod_doc: str) -> str:
	"""RIDE Print Format name for an SRI document code; raises on unknown codes."""
	try:
		return RIDE_PRINT_FORMATS[cod_doc]
	except KeyError:
		raise ValueError(_("Unknown SRI document code '{}'.").format(cod_doc)) from None


def build_attachments(
	xml_file_id: str, cod_doc: str = "01", doctype: str | None = None, name: str | None = None
) -> list:
	"""Queue-ready attachments: the signed XML file plus the on-demand RIDE PDF."""
	attachments = [{"fid": xml_file_id}]
	if doctype and name:
		attachments.append(
			{
				"print_format_attachment": 1,
				"doctype": doctype,
				"name": name,
				"print_format": ride_print_format(cod_doc),
			}
		)
	return attachments


def _party_contact_email(party_doctype: str, party: str) -> str | None:
	contact = frappe.db.get_value(
		"Contact",
		{"link_doctype": party_doctype, "link_name": party, "is_primary_contact": 1},
		"email_id",
	)
	return contact


def _party_lookup(reference_doctype: str) -> tuple:
	"""Party DocType and reference field used to resolve the email recipient."""
	if reference_doctype == "Purchase Invoice":
		return ("Supplier", "supplier")
	if reference_doctype in ("Sales Invoice", "Delivery Note"):
		return ("Customer", "customer")
	raise ValueError(_("Unknown reference doctype '{}'.").format(reference_doctype))


def send_authorized_voucher_mail(voucher_name: str):
	"""Queue the authorized-voucher email with XML+PDF; None when skipped."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to send voucher mail.")
	from l10n_ec.ecuador_localization.voucher_flow import read_voucher_xml

	voucher = frappe.get_doc("SRI Electronic Voucher", voucher_name)
	if voucher.voucher_state != "Authorized":
		return None
	party_doctype, reference_field = _party_lookup(voucher.reference_doctype)
	party = frappe.db.get_value(voucher.reference_doctype, voucher.reference_name, reference_field)
	recipients = []
	if party:
		recipients = resolve_recipients(
			frappe.db.get_value(party_doctype, party, "email_id"),
			_party_contact_email(party_doctype, party),
		)
	if not recipients:
		return None
	xml_file_id = frappe.db.get_value("File", {"file_url": voucher.signed_xml}, "name")
	if not xml_file_id:
		return None
	cod_doc = getattr(voucher, "sri_doc_code", "01")
	return frappe.sendmail(
		recipients=recipients,
		subject=authorized_mail_subject(voucher.access_key),
		message=_("Your electronic voucher was authorized by the SRI."),
		attachments=build_attachments(
			xml_file_id, cod_doc, voucher.reference_doctype, voucher.reference_name
		),
		reference_doctype="SRI Electronic Voucher",
		reference_name=voucher_name,
	)
