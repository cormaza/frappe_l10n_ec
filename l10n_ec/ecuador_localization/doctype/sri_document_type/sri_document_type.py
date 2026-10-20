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


class SRIDocumentType(Document):
	"""Frappe v16 DocType controller for SRI voucher type codes (`codDoc`).

	Codes are enforced at schema level via the `code` Select options, matching
	the SRI electronic invoicing specification exactly.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Literal["01", "03", "04", "05", "06", "07", "41"]
		title: DF.Data
