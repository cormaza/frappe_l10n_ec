"""Unit tests for SRI import settlement arithmetic (T1: CIF + tributes)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.import_settlement import (
	compute_ad_valorem,
	compute_cif,
	compute_fodinfa,
	compute_import_taxes,
	compute_iva,
	compute_iva_base,
)


class TestCifComposition(UnitTestCase):
	def test_cif_sums_fob_freight_insurance(self) -> None:
		self.assertEqual(compute_cif(1000.0, 200.0, 50.0), 1250.0)

	def test_cif_tolerates_zero_legs(self) -> None:
		self.assertEqual(compute_cif(1000.0, 0.0, 0.0), 1000.0)

	def test_cif_rounds_to_two_decimals(self) -> None:
		self.assertEqual(compute_cif(100.0, 10.127, 0.0), 110.13)
		self.assertEqual(compute_cif(100.0, 10.122, 0.0), 110.12)

	def test_cif_negative_leg_fails(self) -> None:
		with self.assertRaises(ValueError):
			compute_cif(1000.0, -1.0, 50.0)


class TestTributeRates(UnitTestCase):
	def test_ad_valorem_applies_rate_to_cif(self) -> None:
		self.assertEqual(compute_ad_valorem(1250.0, 10.0), 125.0)

	def test_fodinfa_applies_rate_to_cif(self) -> None:
		self.assertEqual(compute_fodinfa(1250.0, 0.5), 6.25)

	def test_zero_rate_is_valid_exemption(self) -> None:
		self.assertEqual(compute_ad_valorem(1250.0, 0.0), 0.0)
		self.assertEqual(compute_fodinfa(1250.0, 0.0), 0.0)

	def test_missing_rate_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			compute_ad_valorem(1250.0, None)
		with self.assertRaises(ValueError):
			compute_fodinfa(1250.0, None)

	def test_negative_rate_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			compute_ad_valorem(1250.0, -5.0)


class TestIvaBaseArt59(UnitTestCase):
	def test_iva_base_sums_customs_value_plus_duties(self) -> None:
		# LRTI Art. 59: valor en aduana + impuestos, aranceles, tasas,
		# derechos, recargos y otros gastos de la declaracion.
		self.assertEqual(compute_iva_base(1250.0, 125.0, 6.25), 1381.25)

	def test_iva_base_includes_ice_and_other_duties(self) -> None:
		self.assertEqual(compute_iva_base(1250.0, 125.0, 6.25, ice=100.0, other_duties=10.0), 1491.25)

	def test_iva_applies_rate_to_base(self) -> None:
		self.assertEqual(compute_iva(1381.25, 15.0), 207.19)

	def test_iva_base_negative_component_fails(self) -> None:
		with self.assertRaises(ValueError):
			compute_iva_base(1250.0, -125.0, 6.25)


class TestSettleImport(UnitTestCase):
	def test_full_chain_returns_all_intermediates(self) -> None:
		result = compute_import_taxes(
			fob=1000.0,
			freight=200.0,
			insurance=50.0,
			ad_valorem_rate_pct=10.0,
			fodinfa_rate_pct=0.5,
			iva_rate_pct=15.0,
		)
		self.assertEqual(result["cif"], 1250.0)
		self.assertEqual(result["ad_valorem"], 125.0)
		self.assertEqual(result["fodinfa"], 6.25)
		self.assertEqual(result["iva_base"], 1381.25)
		self.assertEqual(result["iva"], 207.19)

	def test_full_chain_with_ice(self) -> None:
		result = compute_import_taxes(
			fob=1000.0,
			freight=200.0,
			insurance=50.0,
			ad_valorem_rate_pct=10.0,
			fodinfa_rate_pct=0.5,
			iva_rate_pct=15.0,
			ice=100.0,
		)
		self.assertEqual(result["iva_base"], 1481.25)
		self.assertEqual(result["iva"], 222.19)
