"""Contact tax identification hook contract for Customer/Supplier validation.

Phase 3 wiring calls :func:`validate_contact_tax_id` from the `validate` hook
and converts the `ValueError` into `frappe.throw`. Gating uses the Country
ISO code (`EC`), resolved from the contact address by the caller, so this
module stays free of `frappe` imports and testable in Ring 1.
"""

from l10n_ec.sri.identification import validate_identification

ECUADOR_COUNTRY_CODE = "EC"


def is_ecuadorian_contact(country_code: str | None) -> bool:
	"""Whether contact-level SRI validation applies, gated by Country ISO code."""
	return (country_code or "").strip().upper() == ECUADOR_COUNTRY_CODE


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
			f"Invalid tax identification '{(tax_id or '').strip()}'"
			f" for type '{(identification_type_code or '').strip()}'."
		)
