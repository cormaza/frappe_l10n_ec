import unittest

from l10n_ec.ecuador_localization.validation import (
	is_ecuadorian_contact,
	validate_contact_tax_id,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestContactTaxValidation(UnitTestCase):
	"""Unit tests for the Customer/Supplier tax ID hook contract (Phase 3 wiring)."""

	def test_ecuador_iso_code_detection(self) -> None:
		self.assertTrue(is_ecuadorian_contact("EC"))
		self.assertTrue(is_ecuadorian_contact(" ec "))
		self.assertFalse(is_ecuadorian_contact("CO"))
		self.assertFalse(is_ecuadorian_contact("Ecuador"))
		self.assertFalse(is_ecuadorian_contact(""))
		self.assertFalse(is_ecuadorian_contact(None))

	def test_valid_ecuadorian_tax_id_passes(self) -> None:
		validate_contact_tax_id("EC", "04", "1790016919001")
		validate_contact_tax_id("EC", "05", "1710034065")
		validate_contact_tax_id("EC", "07", "9999999999999")

	def test_invalid_ecuadorian_tax_id_raises(self) -> None:
		with self.assertRaises(ValueError):
			validate_contact_tax_id("EC", "04", "1790016819001")
		with self.assertRaises(ValueError):
			validate_contact_tax_id("EC", "05", "1710034066")

	def test_non_ecuadorian_contact_skips_validation(self) -> None:
		validate_contact_tax_id("CO", "04", "not-a-ruc")
		validate_contact_tax_id("", "04", "not-a-ruc")
		validate_contact_tax_id(None, "04", "not-a-ruc")
