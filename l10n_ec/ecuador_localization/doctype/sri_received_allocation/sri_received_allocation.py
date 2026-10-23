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


class SRIReceivedAllocation(Document):
	"""One invoice leg of a customer-issued withholding slip (child table)."""

	if TYPE_CHECKING:
		from frappe.types import DF

		sales_invoice: DF.Link
		ir_value: DF.Currency | None
		iva_value: DF.Currency | None
