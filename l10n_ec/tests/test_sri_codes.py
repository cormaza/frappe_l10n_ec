"""Unit tests for SRI code-with-legend selectors (pure, no frappe)."""

import unittest

from l10n_ec.sri.codes import sri_code


class TestSriCode(unittest.TestCase):
	def test_bare_code_passes_through(self) -> None:
		self.assertEqual(sri_code("02"), "02")
		self.assertEqual(sri_code("1"), "1")

	def test_legend_strips_to_code(self) -> None:
		self.assertEqual(sri_code("02 - Sin crédito tributario"), "02")
		self.assertEqual(sri_code("1 - Bienes 30%"), "1")
		self.assertEqual(sri_code("19 - Tarjeta de crédito"), "19")

	def test_empty_and_none_stay_empty(self) -> None:
		self.assertEqual(sri_code(""), "")
		self.assertEqual(sri_code(None), "")
		self.assertEqual(sri_code("   "), "")


class TestLegendReaders(unittest.TestCase):
	def test_validate_sustento_accepts_legend(self) -> None:
		from l10n_ec.sri.sustentos import validate_sustento

		validate_sustento("02 - Sin crédito tributario")
		validate_sustento("02")
