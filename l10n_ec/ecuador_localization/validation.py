"""Contact tax identification hook contract for Customer/Supplier validation.

Phase 3 wiring calls :func:`validate_contact_tax_id` from the `validate` hook
and converts the `ValueError` into `frappe.throw`. Kept free of `frappe`
imports so the contract stays testable in Ring 1.
"""

from l10n_ec.sri.identification import validate_identification

ECUADOR_COUNTRY = "Ecuador"


def is_ecuadorian_contact(country: str | None) -> bool:
	"""Whether contact-level SRI validation applies, gated by country."""
	return (country or "").strip().lower() == ECUADOR_COUNTRY.lower()


def validate_contact_tax_id(
	country: str | None,
	identification_type_code: str | None,
	tax_id: str | None,
) -> None:
	"""Validate a contact tax ID, skipping non-Ecuadorian contacts silently.

	Raises `ValueError` with an English message when an Ecuadorian contact
	carries an invalid identification number.
	"""
	if not is_ecuadorian_contact(country):
		return
	if not validate_identification(identification_type_code or "", tax_id or ""):
		raise ValueError(
			f"Invalid tax identification '{(tax_id or '').strip()}'"
			f" for type '{(identification_type_code or '').strip()}'."
		)
