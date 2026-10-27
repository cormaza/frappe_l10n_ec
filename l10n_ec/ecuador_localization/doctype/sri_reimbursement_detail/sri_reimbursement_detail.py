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


class SRIReimbursementDetail(Document):
	"""One reimbursed voucher leg (ATS reembolso + factura reembolsoDetalle)."""

	if TYPE_CHECKING:
		from frappe.types import DF

		doc_code: DF.Data
		supplier_id_type: DF.Data
		supplier_id: DF.Data
		sri_number: DF.Data
		issue_date: DF.Date
		auth_number: DF.Data
		base_amount: DF.Currency
		taxed_base: DF.Currency | None
		no_tax_base: DF.Currency | None
		exempt_base: DF.Currency | None
		ice_amount: DF.Currency | None
		iva_amount: DF.Currency | None
