"""Unit tests for exterior treaty rates (pure, sourced, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.treaties import PARAISO_RATE, SIN_CONVENIO_RATE, treaty_rate


class TestTreatyRates(UnitTestCase):
	def test_domestic_rates(self) -> None:
		self.assertEqual(SIN_CONVENIO_RATE, 25.0)
		self.assertEqual(PARAISO_RATE, 37.0)

	def test_espana_canon_10(self) -> None:
		rate, source = treaty_rate("ES", "501A")
		self.assertEqual(rate, 10.0)
		self.assertIn("BOE", source)

	def test_espana_dividendo_15(self) -> None:
		rate, source = treaty_rate("ES", "504")
		self.assertEqual(rate, 15.0)
		self.assertIn("art. 10", source)

	def test_unknown_pair_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			treaty_rate("ES", "312")
		with self.assertRaises(ValueError):
			treaty_rate("XX", "501A")
