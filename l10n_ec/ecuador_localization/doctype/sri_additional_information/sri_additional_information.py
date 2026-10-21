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


class SRIAdditionalInformation(Document):
	"""Frappe v16 DocType controller for permanent central infoAdicional entries.

	One record per company holds the standing `infoAdicional` name/value
	pairs (`SRI Additional Information Entry` rows) merged into every
	emitted voucher after transactional rows. Disabled records are ignored.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		title: DF.Data
		company: DF.Link
		enabled: DF.Check
		entries: DF.Table
