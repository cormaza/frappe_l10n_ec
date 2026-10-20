import unittest

from l10n_ec.ecuador_localization.validation import (
	is_ecuadorian_contact,
	is_foreign_contact,
	is_generic_final_consumer,
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

	def test_foreign_contact_needs_a_resolved_non_ec_code(self) -> None:
		self.assertTrue(is_foreign_contact("CO"))
		self.assertTrue(is_foreign_contact("us"))
		self.assertFalse(is_foreign_contact("EC"))
		self.assertFalse(is_foreign_contact(""))
		self.assertFalse(is_foreign_contact(None))

	def test_generic_final_consumer_covers_type_and_id(self) -> None:
		self.assertTrue(is_generic_final_consumer("07", "9999999999999"))
		self.assertTrue(is_generic_final_consumer("07", "anything"))
		self.assertTrue(is_generic_final_consumer("04", "9999999999999"))
		self.assertFalse(is_generic_final_consumer("04", "1790016919001"))
		self.assertFalse(is_generic_final_consumer(None, None))
