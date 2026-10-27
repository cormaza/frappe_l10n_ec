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

from l10n_ec.sri.import_settlement import validate_partida


class SRIImportAssumption(Document):
	"""One company-owned import case: item + partida + last seen AD VALOREM.

	Estimates only: rates prefill settlements, the DAI crosscheck always
	arbitrates. A crosscheck mismatch means the tariff moved — update the
	row (and its source DAI) instead of forcing the settlement.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		naming_series: DF.Data
		company: DF.Link
		item_code: DF.Link
		partida: DF.Data
		ad_valorem_rate: DF.Percent
		source_dai: DF.Data | None

	def validate(self) -> None:
		try:
			validate_partida(getattr(self, "partida", None))
		except ValueError as exc:
			if frappe is not None:
				frappe.throw(str(exc))
			raise
		if frappe is None:  # pragma: no cover
			return
		duplicates = frappe.db.get_all(
			"SRI Import Assumption",
			filters={"company": self.company, "item_code": self.item_code, "name": ["!=", self.name or ""]},
			pluck="name",
		)
		if duplicates:
			frappe.throw(
				f"Company '{self.company}' already assumes item '{self.item_code}' ({duplicates[0]}): edit it instead of duplicating."
			)
