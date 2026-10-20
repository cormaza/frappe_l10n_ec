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


class SRIIdentificationType(Document):
	"""Frappe v16 DocType controller for SRI taxpayer identification types (`04`-`08`).

	Codes are enforced at schema level via the `code` Select options, matching
	the SRI electronic invoicing specification exactly. Format checks against
	`l10n_ec/sri/identification.py` happen at the contact-validation layer.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Literal["04", "05", "06", "07", "08"]
		title: DF.Data
