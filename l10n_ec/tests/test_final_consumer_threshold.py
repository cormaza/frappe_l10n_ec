import unittest

from l10n_ec.ecuador_localization.validation import validate_final_consumer_amount

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestFinalConsumerThreshold(UnitTestCase):
	"""Unit tests for the Consumidor Final USD 50.00 invoice rule (Phase 6D)."""

	def test_at_and_under_threshold_pass(self) -> None:
		validate_final_consumer_amount("07", "9999999999999", 50.00)
		validate_final_consumer_amount("07", "9999999999999", 12.34)

	def test_over_threshold_raises(self) -> None:
		with self.assertRaises(ValueError):
			validate_final_consumer_amount("07", "9999999999999", 50.01)

	def test_generic_consumer_by_id_is_covered(self) -> None:
		with self.assertRaises(ValueError):
			validate_final_consumer_amount("04", "9999999999999", 100.00)

	def test_identified_buyers_are_unaffected(self) -> None:
		validate_final_consumer_amount("04", "1790016919001", 10000.00)
		validate_final_consumer_amount("05", "1710034065", 999.99)

	def test_custom_threshold(self) -> None:
		validate_final_consumer_amount("07", "9999999999999", 200.00, threshold=200.00)
		with self.assertRaises(ValueError):
			validate_final_consumer_amount("07", "9999999999999", 200.01, threshold=200.00)
