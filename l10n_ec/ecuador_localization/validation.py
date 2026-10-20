"""Contact tax identification hook contract for Customer/Supplier validation.

Phase 3 wiring calls :func:`validate_contact_tax_id` from the `validate` hook
and converts the `ValueError` into `frappe.throw`. Gating uses the Country
ISO code (`EC`), resolved from the contact address by the caller, so this
module stays free of `frappe` imports and testable in Ring 1.
"""

from l10n_ec.sri.identification import FINAL_CONSUMER_ID, validate_identification

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


ECUADOR_COUNTRY_CODE = "EC"
FINAL_CONSUMER_THRESHOLD = 50.00


def is_ecuadorian_contact(country_code: str | None) -> bool:
	"""Whether contact-level SRI validation applies, gated by Country ISO code."""
	return (country_code or "").strip().upper() == ECUADOR_COUNTRY_CODE


def is_foreign_contact(country_code: str | None) -> bool:
	"""Whether the contact is identifiably foreign (resolved non-EC ISO code).

	An unresolvable country (None/empty) is unknown, not foreign. Resolve it
	from the primary Address Country; never from Territory, which is a sales
	concept, not a nationality.
	"""
	code = (country_code or "").strip().upper()
	return bool(code) and code != ECUADOR_COUNTRY_CODE


def is_generic_final_consumer(identification_type_code: str | None, tax_id: str | None) -> bool:
	"""Whether the record is the generic final consumer (type or ID), all spellings."""
	code = (identification_type_code or "").strip()
	cleaned = (tax_id or "").strip()
	return code == "07" or cleaned == FINAL_CONSUMER_ID


def validate_contact_tax_id(
	country_code: str | None,
	identification_type_code: str | None,
	tax_id: str | None,
) -> None:
	"""Validate a contact tax ID, skipping non-Ecuadorian contacts silently.

	Raises `ValueError` with an English message when an Ecuadorian contact
	carries an invalid identification number.
	"""
	if not is_ecuadorian_contact(country_code):
		return
	if not validate_identification(identification_type_code or "", tax_id or ""):
		raise ValueError(
			_("Invalid tax identification '{}' for type '{}'.").format(
				(tax_id or "").strip(), (identification_type_code or "").strip()
			)
		)


def validate_final_consumer_amount(
	identification_type_code: str | None,
	tax_id: str | None,
	total: float | None,
	threshold: float = FINAL_CONSUMER_THRESHOLD,
) -> None:
	"""Reject over-threshold invoices to the generic final consumer.

	Only the generic consumer identity (type `07` or the fixed ID) is
	checked; identified buyers are unaffected. Multi-currency conversion
	is out of scope: totals compare directly against the USD threshold.
	"""
	if not is_generic_final_consumer(identification_type_code, tax_id):
		return
	if (total or 0) > threshold:
		raise ValueError(
			_(
				"Sales to Consumidor Final above {} are not allowed; register the buyer identification."
			).format(threshold)
		)
