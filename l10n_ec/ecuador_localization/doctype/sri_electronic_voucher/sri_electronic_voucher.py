from __future__ import annotations

from typing import TYPE_CHECKING

try:
	import frappe
	from frappe.model.document import Document
except ImportError:  # pragma: no cover

	class Document:  # type: ignore[no-redef]
		"""Fallback base class when imported outside a Frappe Bench environment."""

		def __init__(self, *args, **kwargs):
			for key, value in kwargs.items():
				setattr(self, key, value)

	frappe = None  # type: ignore[assignment]


class SRIElectronicVoucher(Document):
	"""Frappe v16 DocType controller for SRI electronic voucher tracking.

	State transitions are owned exclusively by
	`l10n_ec.ecuador_localization.voucher_flow`; this controller carries no
	transition logic so the machine stays testable without frappe.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		access_key: DF.Data
		authorization_date: DF.Datetime | None
		authorization_number: DF.Data | None
		column_break_authorization: DF.ColumnBreak
		column_break_reference: DF.ColumnBreak
		company: DF.Link
		last_message: DF.SmallText | None
		reference_doctype: DF.Literal["Sales Invoice", "Purchase Invoice", "Delivery Note"]
		reference_name: DF.DynamicLink
		section_break_messages: DF.SectionBreak
		section_break_xml: DF.SectionBreak
		signed_xml: DF.Attach | None
		unsigned_xml: DF.Attach | None
		sri_doc_code: DF.Literal["01", "03", "04", "05", "06", "07"]
		sri_number: DF.Data | None
		voucher_state: DF.Literal["Generated", "Signed", "Received", "Authorized", "Returned", "Rejected"]
