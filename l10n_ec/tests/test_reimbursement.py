"""Unit tests for SRI reimbursement detail (T1: independent entity + totals)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.validation import (
	validate_reimbursement_details,
	validate_sustento_code,
)
from l10n_ec.sri.reimbursement import (
	calc_reimbursement_total,
	resolve_reimbursement_total,
	validate_sustento_for_doc,
)


class TestSustentoDocCrossTable(UnitTestCase):
	def test_intermediary_sustento_08_with_factura_passes(self) -> None:
		validate_sustento_for_doc("08", "01")

	def test_intermediary_sustento_08_with_liquidacion_passes(self) -> None:
		validate_sustento_for_doc("08", "03")

	def test_intermediary_sustento_08_with_reembolso_sale_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_sustento_for_doc("08", "41")

	def test_mandante_reembolso_sale_with_sustento_01_passes(self) -> None:
		validate_sustento_for_doc("01", "41")

	def test_unknown_sustento_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_sustento_for_doc("99", "01")


class TestReimbursementTotal(UnitTestCase):
	def _lines(self):
		return [
			{"base_amount": 100.0},
			{"base_amount": 50.5},
		]

	def test_calc_sums_base_amounts(self) -> None:
		self.assertEqual(calc_reimbursement_total(self._lines()), 150.5)

	def test_resolve_defaults_to_calculated(self) -> None:
		self.assertEqual(resolve_reimbursement_total(self._lines(), None, False), 150.5)

	def test_override_without_optin_fails(self) -> None:
		with self.assertRaises(ValueError):
			resolve_reimbursement_total(self._lines(), 10.0, False)

	def test_zero_override_reads_as_no_override(self) -> None:
		# Bench Currency fields default to 0.0: untouched reads as calculated.
		self.assertEqual(resolve_reimbursement_total(self._lines(), 0.0, False), 150.5)
		self.assertEqual(resolve_reimbursement_total(self._lines(), 0, False), 150.5)

	def test_override_with_optin_wins(self) -> None:
		self.assertEqual(resolve_reimbursement_total(self._lines(), 10.0, True), 10.0)


class TestReimbursementValidation(UnitTestCase):
	def test_reimbursement_flag_without_lines_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_reimbursement_details({"doctype": "Purchase Invoice", "sri_is_reimbursement": 1})

	def test_override_without_optin_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_reimbursement_details(
				{
					"doctype": "Purchase Invoice",
					"sri_is_reimbursement": 1,
					"sri_reimbursement_details": [{"base_amount": 100.0}],
					"sri_reimbursement_override_value": 10.0,
				}
			)

	def test_sustento_08_with_41_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_sustento_code(
				{
					"doctype": "Purchase Invoice",
					"sri_sustento_code": "08",
					"sri_is_reimbursement": 1,
				}
			)

	def test_sustento_01_with_41_passes(self) -> None:
		validate_sustento_code(
			{
				"doctype": "Purchase Invoice",
				"sri_sustento_code": "01",
				"sri_is_reimbursement": 1,
			}
		)
