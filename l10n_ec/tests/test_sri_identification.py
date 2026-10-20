import unittest

from l10n_ec.sri.identification import (
	validate_ci,
	validate_identification,
	validate_ruc,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestSRIIdentification(UnitTestCase):
	"""Unit tests for Ecuadorian taxpayer identification validation (SRI types 04-08)."""

	def test_valid_ruc(self) -> None:
		self.assertTrue(validate_ruc("1790016919001"))

	def test_ruc_with_wrong_check_digit_is_invalid(self) -> None:
		self.assertFalse(validate_ruc("1790016819001"))

	def test_ruc_rejects_malformed_input(self) -> None:
		self.assertFalse(validate_ruc("17900169190"))
		self.assertFalse(validate_ruc("179001691900A"))
		self.assertFalse(validate_ruc(""))

	def test_valid_cedula(self) -> None:
		self.assertTrue(validate_ci("1710034065"))

	def test_cedula_with_wrong_check_digit_is_invalid(self) -> None:
		self.assertFalse(validate_ci("1710034066"))

	def test_cedula_rejects_malformed_input(self) -> None:
		self.assertFalse(validate_ci("171003406"))
		self.assertFalse(validate_ci("171003406A"))
		self.assertFalse(validate_ci(""))

	def test_dispatch_by_sri_type_code(self) -> None:
		self.assertTrue(validate_identification("04", "1790016919001"))
		self.assertFalse(validate_identification("04", "1790016819001"))
		self.assertTrue(validate_identification("05", "1710034065"))
		self.assertFalse(validate_identification("05", "1710034066"))
		self.assertTrue(validate_identification("06", "P1234567"))
		self.assertFalse(validate_identification("06", "   "))
		self.assertTrue(validate_identification("07", "9999999999999"))
		self.assertFalse(validate_identification("07", "1790016919001"))
		self.assertTrue(validate_identification("08", "EXT-98765"))
		self.assertFalse(validate_identification("08", ""))

	def test_unknown_type_code_is_invalid(self) -> None:
		self.assertFalse(validate_identification("09", "1790016919001"))
		self.assertFalse(validate_identification("", "1790016919001"))

	def test_inputs_are_stripped_before_validation(self) -> None:
		self.assertTrue(validate_identification("04", "  1790016919001  "))
		self.assertTrue(validate_identification("07", "9999999999999\n"))
