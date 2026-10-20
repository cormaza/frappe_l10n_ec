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


class SRIEmissionSequence(Document):
	"""Child table row holding the current 9-digit sequence for one SRI document type."""

	if TYPE_CHECKING:
		from frappe.types import DF

		current_sequence: DF.Int
		document_type: DF.Link
