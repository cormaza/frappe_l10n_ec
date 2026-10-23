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


class SRIReceivedWithholding(Document):
	"""One customer-issued withholding slip covering many sales invoices.

	Customer-side (received) withholdings: the customer withholds IR/IVA
	at payment time and issues a single Comprobante de Retencion for
	several of our invoices. This document plans the per-invoice split;
	settlement posts per invoice when the linked Payment Entry submits
	(`received_settlement`). Supplier-side emission (`voucher_flow`) is a
	separate flow and never reads this doctype.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		customer: DF.Link
		company: DF.Link
		retencion_number: DF.Data
		authorization: DF.Data | None
		retencion_date: DF.Date | None
		access_key: DF.Data | None
		payment_entry: DF.Link | None
		allocations: DF.Table

	def validate(self) -> None:
		"""Validate allocations on save (bench only; pure checks below)."""
		if frappe is None:  # pragma: no cover
			return
		from l10n_ec.ecuador_localization.received_batch import validate_allocations

		validate_allocations(self)

	def on_submit(self) -> None:
		"""Stamp the shared slip onto allocated invoices (bench only)."""
		if frappe is None:  # pragma: no cover
			return
		from l10n_ec.ecuador_localization.received_settlement import stamp_slip_references

		stamp_slip_references(self.name, True)

	def on_cancel(self) -> None:
		"""Unstamp unless a settlement JE already posted (bench only)."""
		if frappe is None:  # pragma: no cover
			return
		from l10n_ec.ecuador_localization.received_settlement import stamp_slip_references

		try:
			stamp_slip_references(self.name, False)
		except ValueError as exc:
			frappe.throw(str(exc))
