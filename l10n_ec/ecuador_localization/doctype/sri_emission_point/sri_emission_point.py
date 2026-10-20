from __future__ import annotations

import re
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

ESTABLISHMENT_PATTERN = re.compile(r"^\d{3}$")
MAX_SEQUENCE = 999999999


def _reject(message: str) -> None:
	if frappe:
		frappe.throw(frappe._(message))
	raise ValueError(message)


class SRIEmissionPoint(Document):
	"""Frappe v16 DocType controller for SRI emission points (`Establecimiento` + `Punto de Emisión`).

	Both codes are exactly 3 digits per the SRI electronic invoicing specification.
	Per-document-type 9-digit sequences live in the `sequences` child table.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		from l10n_ec.ecuador_localization.doctype.sri_emission_sequence.sri_emission_sequence import (
			SRIEmissionSequence,
		)

		column_break_setup: DF.ColumnBreak
		company: DF.Link | None
		emission_point_code: DF.Data
		establishment_code: DF.Data
		sequences: DF.Table[SRIEmissionSequence]

	def validate(self) -> None:
		for fieldname in ("establishment_code", "emission_point_code"):
			value = (getattr(self, fieldname, None) or "").strip()
			if not ESTABLISHMENT_PATTERN.match(value):
				_reject("SRI emission code '{}' must be exactly 3 numeric digits.".format(value))
		for row in getattr(self, "sequences", None) or []:
			if not getattr(row, "document_type", None):
				_reject("Every SRI emission sequence row requires a document type.")
			sequence = getattr(row, "current_sequence", 0) or 0
			if not 0 <= sequence <= MAX_SEQUENCE:
				_reject("SRI sequence {} must be between 0 and {}.".format(sequence, MAX_SEQUENCE))
