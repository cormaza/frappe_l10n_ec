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


class TestPosTicketThreshold(UnitTestCase):
	"""Per-ticket CF rule: the POS ticket is the transaction, not the merge."""

	def test_all_tickets_under_threshold_pass(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_pos_tickets

		validate_pos_tickets("07", "9999999999999", [30.00, 30.00, 30.00])

	def test_single_ticket_over_threshold_raises(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_pos_tickets

		with self.assertRaises(ValueError):
			validate_pos_tickets("07", "9999999999999", [30.00, 50.01])

	def test_identified_buyers_are_unaffected(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_pos_tickets

		validate_pos_tickets("04", "1790016919001", [5000.00])

	def test_empty_merge_passes(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_pos_tickets

		validate_pos_tickets("07", "9999999999999", [])


class TestTicketEmissionPoint(UnitTestCase):
	"""A ticket keeps its profile emission point; drift fails loud."""

	def test_matching_or_empty_point_passes(self) -> None:
		from l10n_ec.ecuador_localization.invoice_hooks import ensure_ticket_point

		ensure_ticket_point(None, " emission-001", "t1")
		ensure_ticket_point("emission-001", "emission-001", "t1")

	def test_drift_fails_loud(self) -> None:
		from l10n_ec.ecuador_localization.invoice_hooks import ensure_ticket_point

		with self.assertRaises(ValueError):
			ensure_ticket_point("emission-002", "emission-001", "t1")


class TestFacturaCfSingleVoucher(UnitTestCase):
	"""A single factura voucher to generic CF over 50 is SRI-rejected; fail at origin."""

	def test_single_cf_over_threshold_raises(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_factura_cf_total

		with self.assertRaises(ValueError):
			validate_factura_cf_total("07", "9999999999999", 80.00)

	def test_single_cf_at_threshold_passes(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_factura_cf_total

		validate_factura_cf_total("07", "9999999999999", 50.00)

	def test_identified_buyer_unaffected(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_factura_cf_total

		validate_factura_cf_total("04", "1790016919001", 8000.00)
