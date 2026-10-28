"""Unit tests for SRI import declaration (T3: file import + crosscheck)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.import_declaration import (
	CROSSCHECK_TOLERANCE,
	crosscheck_settlement,
	parse_declaration_csv,
)


def _costs():
	return {"fob": 1000.0, "freight": 200.0, "insurance": 50.0}


def _rates():
	return {"ad_valorem": 10.0, "fodinfa": 0.5, "iva": 15.0}


def _declared():
	return {"dai_ad_valorem": 125.0, "dai_fodinfa": 6.25, "dai_iva": 207.19, "dai_total": 338.44}


class TestParseDeclarationCsv(UnitTestCase):
	HEADER = "dai_number,dai_date,ad_valorem_rate,fodinfa_rate,iva_rate,ice,other_duties,dai_ad_valorem,dai_fodinfa,dai_iva,dai_total"
	ROW = "123-2026-10-000001,2026-10-15,10.0,0.5,15.0,0.0,0.0,125.0,6.25,207.19,338.44"

	def test_parse_canonical_row(self) -> None:
		parsed = parse_declaration_csv(self.HEADER + "\n" + self.ROW)
		self.assertEqual(parsed["dai_number"], "123-2026-10-000001")
		self.assertEqual(parsed["rates"]["ad_valorem"], 10.0)
		self.assertEqual(parsed["declared"]["dai_iva"], 207.19)

	def test_wrong_header_fails(self) -> None:
		with self.assertRaises(ValueError):
			parse_declaration_csv("fobola\n1")

	def test_two_rows_fail_single_declaration_expected(self) -> None:
		with self.assertRaises(ValueError):
			parse_declaration_csv(self.HEADER + "\n" + self.ROW + "\n" + self.ROW)

	def test_non_numeric_rate_fails(self) -> None:
		bad = self.ROW.replace("10.0,0.5", "diez,0.5")
		with self.assertRaises(ValueError):
			parse_declaration_csv(self.HEADER + "\n" + bad)


class TestCrosscheck(UnitTestCase):
	def test_matching_declaration_passes(self) -> None:
		result = crosscheck_settlement(_costs(), _rates(), _declared())
		self.assertTrue(result["matched"])
		self.assertEqual(result["computed"]["cif"], 1250.0)
		self.assertEqual(result["differences"], {})

	def test_cent_rounding_drift_passes(self) -> None:
		declared = _declared()
		declared["dai_iva"] = 207.20
		result = crosscheck_settlement(_costs(), _rates(), declared)
		self.assertTrue(result["matched"])

	def test_wrong_rate_fails_with_named_culprit(self) -> None:
		declared = _declared()
		declared["dai_ad_valorem"] = 250.0
		with self.assertRaises(ValueError) as ctx:
			crosscheck_settlement(_costs(), _rates(), declared)
		self.assertIn("dai_ad_valorem", str(ctx.exception))

	def test_missing_declared_key_fails(self) -> None:
		declared = _declared()
		del declared["dai_iva"]
		with self.assertRaises(ValueError):
			crosscheck_settlement(_costs(), _rates(), declared)

	def test_tolerance_is_documented_one_dollar(self) -> None:
		self.assertEqual(CROSSCHECK_TOLERANCE, 1.00)


class TestTwoPartidaDaiSelfHeals(unittest.TestCase):
	"""Edge pack D (S1/S2/S6): one DAI, two partidas, stale assumption fails loud.

	Partida X settles clean at 10%; partida Y moved to 15% but the company
	assumption still estimates 10%: the crosscheck fails naming
	dai_ad_valorem, and re-running with the DAI rate passes (self-heal).
	Covers the T7 tariff-move story at the arithmetic level."""

	def _check(self, rate, declared_ad_valorem):
		return crosscheck_settlement(
			_costs(),
			{"ad_valorem": rate, "fodinfa": 0.5, "iva": 15.0},
			{
				"dai_ad_valorem": declared_ad_valorem,
				"dai_fodinfa": 6.25,
				"dai_iva": 207.19,
				"dai_total": 338.44,
			},
		)

	def test_first_partida_matches_at_10pct(self) -> None:
		result = self._check(10.0, 125.0)
		self.assertTrue(result["matched"])
		self.assertEqual(result["differences"], {})

	def test_stale_assumption_fails_naming_ad_valorem(self) -> None:
		# DAI says 15% (187.50) but the estimate still runs 10%.
		with self.assertRaises(ValueError) as ctx:
			self._check(10.0, 187.50)
		self.assertIn("dai_ad_valorem", str(ctx.exception))

	def test_corrected_rate_self_heals(self) -> None:
		# Same DAI row, estimate updated to the arbitrating 15% rate.
		declared = {
			"dai_ad_valorem": 187.50,
			"dai_fodinfa": 6.25,
			"dai_iva": 216.56,
			"dai_total": 410.31,
		}
		result = crosscheck_settlement(
			_costs(),
			{"ad_valorem": 15.0, "fodinfa": 0.5, "iva": 15.0},
			declared,
		)
		self.assertTrue(result["matched"])
