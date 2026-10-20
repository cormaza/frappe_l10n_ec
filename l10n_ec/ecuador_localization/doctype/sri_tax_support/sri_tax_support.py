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


class SRITaxSupport(Document):
	"""Frappe v16 DocType controller for SRI tax support codes (`codSustento`, ATS Table 5).

	Codes are enforced at schema level via the `code` Select options, matching
	the SRI specification exactly.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Literal[
			"01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15"
		]
		title: DF.Data
