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

from l10n_ec.sri.import_links import LINK_DOCTYPES, validate_settlement_links


class SRIImportSettlement(Document):
	"""Accumulated import costs toward tax settlement (T2: link set only).

	Computation (DAI rates, Art. 59 totals) lands in T3; the Landed Cost
	Voucher prefill lands in T4. This controller only owns the link set:
	which source documents the settlement accumulates.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		naming_series: DF.Data
		company: DF.Link
		supplier: DF.Link
		purchase_order: DF.Link | None
		purchase_receipt: DF.Link | None
		purchase_invoice: DF.Link | None
		freight_invoice: DF.Link | None
		insurance_invoice: DF.Link | None
		dai_number: DF.Data | None
		dai_date: DF.Date | None

	def validate(self) -> None:
		links = {
			role: ((doctype, getattr(self, role, None)) if getattr(self, role, None) else None)
			for role, doctype in LINK_DOCTYPES.items()
		}
		try:
			validate_settlement_links(getattr(self, "company", None), links)
		except ValueError as exc:
			if frappe is not None:
				frappe.throw(str(exc))
			raise
		if frappe is None:  # pragma: no cover
			return
		self._validate_linked_documents(links)

	def _validate_linked_documents(self, links: dict) -> None:
		"""Database checks: existence, same company, not cancelled."""
		for role, ref in links.items():
			if not ref:
				continue
			doctype, name = ref
			values = frappe.db.get_value(doctype, name, ["company", "docstatus"])
			if values is None:
				frappe.throw(f"{doctype} '{name}' linked as {role} does not exist.")
			company, docstatus = values
			if company != self.company:
				frappe.throw(
					f"{doctype} '{name}' belongs to '{company}', not '{self.company}'."
				)
			if docstatus == 2:
				frappe.throw(f"{doctype} '{name}' linked as {role} is cancelled.")
