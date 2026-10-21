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


class SRIAdditionalInformationEntry(Document):
	"""Child table row for one `infoAdicional` name/value pair."""

	if TYPE_CHECKING:
		from frappe.types import DF

		nombre: DF.Data
		valor: DF.SmallText
