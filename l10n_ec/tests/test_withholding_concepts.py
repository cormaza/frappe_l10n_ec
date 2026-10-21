import unittest

from l10n_ec.ecuador_localization.voucher_flow import sustento_entries
from l10n_ec.sri.withholding_concepts import (
	CONCEPTS,
	WITHHOLDING_CONCEPTS_VALID_FROM,
	resolve_concepto,
	validate_concepto_map,
)
from l10n_ec.sri.voucher_states import SriVoucherError

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

EXPECTED = {
	# IR (impuesto '1'): code -> (rate, description).
	"303": (10.0, "Honorarios profesionales"),
	"303A": (5.0, "Servicios profesionales sociedades"),
	"304": (10.0, "Intelecto sin título"),
	"304A": (10.0, "Comisiones intelecto"),
	"304C": (10.0, "Deportistas"),
	"304D": (10.0, "Artistas"),
	"307": (3.0, "Mano de obra"),
	"308": (10.0, "Imagen y renombre"),
	"309": (3.0, "Publicidad"),
	"310": (1.0, "Transporte"),
	"311": (3.0, "Liquidación compra"),
	"312": (2.0, "Bienes muebles"),
	"319": (2.0, "Leasing"),
	"320": (10.0, "Arriendo inmuebles"),
	"322": (2.0, "Seguros"),
	"323": (3.0, "Rendimientos financieros"),
	"332": (0.0, "No sujeto"),
	"343": (1.0, "Otras 1%"),
	"343A": (2.0, "Energía eléctrica"),
	"343B": (2.0, "Construcción"),
	"343C": (2.0, "Botellas PET"),
	"344A": (2.0, "Tarjetas"),
	"344B": (2.0, "Minerales"),
	"3440": (3.0, "Otras 3%"),
	"3482": (5.0, "Comisiones sociedades"),
	# IVA (impuesto '2').
	"1": (30.0, "Bienes"),
	"2": (70.0, "Servicios"),
	"3": (100.0, "Honorarios"),
	"7": (0.0, "Retención cero"),
	"8": (0.0, "No procede"),
	"9": (10.0, "Especial 10%"),
	"10": (20.0, "Especial 20%"),
	"11": (50.0, "Especial 50%"),
}

PURCHASE = {"doc_code": "01", "number": "001-001-000000001"}


class TestWithholdingConcepts(UnitTestCase):
	"""Unit tests for the official SRI withholding concepto table (pure Python)."""

	def test_catalog_covers_all_sourced_codes(self) -> None:
		self.assertEqual(set(CONCEPTS), set(EXPECTED))
		self.assertEqual(len(CONCEPTS), 33)

	def test_all_codes_resolve_with_correct_impuesto_and_rate(self) -> None:
		for code, (rate, description) in EXPECTED.items():
			with self.subTest(code=code):
				expected_impuesto = "2" if code in ("1", "2", "3", "7", "8", "9", "10", "11") else "1"
				impuesto, resolved_rate, resolved_description = resolve_concepto(code)
				self.assertEqual(impuesto, expected_impuesto)
				self.assertEqual(resolved_rate, rate)
				self.assertEqual(resolved_description, description)

	def test_all_codes_share_vigencia(self) -> None:
		self.assertEqual(WITHHOLDING_CONCEPTS_VALID_FROM, "2026-03-01")
		for code in CONCEPTS:
			with self.subTest(code=code):
				self.assertEqual(CONCEPTS[code][3], "2026-03-01")

	def test_unknown_code_raises(self) -> None:
		for bad in ("999", "303B", "", "1 "):
			with self.subTest(code=bad):
				with self.assertRaises(SriVoucherError):
					resolve_concepto(bad)

	def test_validate_concepto_map_accepts_official_pairs(self) -> None:
		self.assertIsNone(
			validate_concepto_map({"Ecuador IR 2%": ("1", "303"), "Ecuador IVA 30%": ("2", "1")})
		)

	def test_validate_concepto_map_rejects_unknown_concepto(self) -> None:
		with self.assertRaises(SriVoucherError):
			validate_concepto_map({"Ecuador IR 2%": ("1", "999")})

	def test_validate_concepto_map_rejects_pending_code(self) -> None:
		with self.assertRaises(SriVoucherError):
			validate_concepto_map({"Ecuador IR 2%": ("1", None)})

	def test_validate_concepto_map_rejects_impuesto_mismatch(self) -> None:
		with self.assertRaises(SriVoucherError):
			validate_concepto_map({"Ecuador IR 2%": ("2", "303")})
		with self.assertRaises(SriVoucherError):
			validate_concepto_map({"Ecuador IVA 30%": ("1", "1")})


class TestSustentoEntriesConceptoValidation(UnitTestCase):
	"""`sustento_entries` fails loud on unknown per-call conceptos (pure Python)."""

	def _row(self, category="Ecuador IR 2%", rate=2.0):
		return [{"category": category, "rate": rate, "taxable": 100.00, "amount": 2.00}]

	def test_valid_concepto_still_resolves(self) -> None:
		entries = sustento_entries(self._row(), PURCHASE, {"Ecuador IR 2%": ("1", "303")})
		self.assertEqual(entries[0]["withholding_code"], "303")
		self.assertEqual(entries[0]["tax_type"], "IR")

	def test_unknown_concepto_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			sustento_entries(self._row(), PURCHASE, {"Ecuador IR 2%": ("1", "999")})

	def test_impuesto_mismatch_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			sustento_entries(self._row(), PURCHASE, {"Ecuador IR 2%": ("2", "303")})

	def test_missing_category_still_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			sustento_entries(self._row(), PURCHASE, {})
