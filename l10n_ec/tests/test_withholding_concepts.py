import unittest

from l10n_ec.ecuador_localization.voucher_flow import sustento_entries
from l10n_ec.sri.voucher_states import SriVoucherError
from l10n_ec.sri.withholding_concepts import (
	CONCEPTS,
	NON_EMITTABLE_IMPUESTOS,
	SOURCES,
	UNMAPPED_CONCEPTS,
	UNMAPPED_PRE2013_EXTERIOR,
	WITHHOLDING_CONCEPTS_VALID_FROM,
	casilleros_for,
	concepto_rate,
	resolve_concepto,
	validate_concepto_map,
)

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

# Spot checks for Phase 9.0 S1 extension rows: code -> (impuesto, rate, description).
SPOT_CHECKS = {
	"304B": (
		"1",
		10.0,
		"Pagos a notarios y registradores de la propiedad y mercantil por sus actividades ejercidas como tales",
	),
	"312C": (
		"1",
		1.75,
		"COMPRAS AL COMERCIALIZADOR: de bienes de origen bioacuático, forestal y los descritos  el art.27.1 de LRTI",
	),
	"323E2": ("1", 0.0, "Rendimientos financieros depósito a plazo fijo exentos"),
	"325": ("1", 25.0, "Anticipo dividendos"),
	"332E": ("1", 0.0, "Valores entregados por las cooperativas de transporte a sus socios"),
	"333": (
		"1",
		10.0,
		"Ganancia en la enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades, que se coticen en bolsa de valores del Ecuador",
	),
	"334": (
		"1",
		2.0,
		"Contraprestación producida por la enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades, no cotizados en bolsa de valores del Ecuador",
	),
	"335": ("1", 15.0, "Loterías, rifas, pronósticos deportivos, apuestas y similares"),
	"340": ("1", 3.0, "Impuesto único a la exportación de banano"),
	"3480": (
		"1",
		15.0,
		"Impuesto a la renta único sobre los ingresos percibidos por los operadores de pronósticos deportivos",
	),
	"500": ("9", None, "Pago a no residentes - Rentas Inmobiliarias"),
	"505D": ("9", None, "Pago a no residentes - Intereses por financiamiento de proveedores externos"),
}

# Codes known but unrated at vigencia: resolve works, rate use-paths raise.
UNRATED = (
	"302",
	"312B",
	"326",
	"327",
	"336",
	"337",
	"338",
	"346B",
	"346D",
	"3481",
	"350",
	"351",
	"500",
	"502",
)

PURCHASE = {"doc_code": "01", "number": "001-001-000000001"}


class TestWithholdingConcepts(UnitTestCase):
	"""Unit tests for the official SRI withholding concepto table (pure Python)."""

	def test_catalog_covers_all_sourced_codes(self) -> None:
		for code, (rate, description) in EXPECTED.items():
			with self.subTest(code=code):
				impuesto, stored_description, stored_rate, _valid_from, _casilleros = CONCEPTS[code]
				self.assertEqual(stored_rate, rate)
				self.assertEqual(stored_description, description)
				self.assertNotIn(impuesto, NON_EMITTABLE_IMPUESTOS)
		self.assertEqual(len(CONCEPTS), 176)

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
		for bad in ("999", "303B", "", "9X", "344C"):
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


class TestWithholdingConceptsExtension(UnitTestCase):
	"""Phase 9.0 S1: full residentes set, casilleros, unrated and exterior rows."""

	def test_every_row_resolves_and_matches_catalog(self) -> None:
		for code, (impuesto, description, rate, _valid_from, _casilleros) in CONCEPTS.items():
			with self.subTest(code=code):
				self.assertEqual(resolve_concepto(code), (impuesto, rate, description))

	def test_spot_checked_extension_rows(self) -> None:
		for code, (impuesto, rate, description) in SPOT_CHECKS.items():
			with self.subTest(code=code):
				self.assertEqual(resolve_concepto(code), (impuesto, rate, description))

	def test_row_shapes_and_impuestos(self) -> None:
		for code, row in CONCEPTS.items():
			with self.subTest(code=code):
				self.assertEqual(len(row), 5)
				impuesto, _description, _rate, _valid_from, casilleros = row
				self.assertIn(impuesto, ("1", "2", "9"))
				if casilleros is not None:
					self.assertIsInstance(casilleros, tuple)
					self.assertTrue(casilleros)
					for casillero in casilleros:
						self.assertIsInstance(casillero, int)
				if impuesto == "9":
					self.assertIsNone(row[2])

	def test_every_row_has_source_note(self) -> None:
		self.assertEqual(set(SOURCES), set(CONCEPTS))
		for code, note in SOURCES.items():
			with self.subTest(code=code):
				self.assertTrue(note)

	def test_casilleros_for_sighted_pairs(self) -> None:
		pairs = {
			"303": (303, 353),
			"303A": (3030, 3530),
			"304B": (304, 354),
			"312A": (3120, 3620),
			"312C": (3121, 3621),
			"314A": (314, 364),
			"323E": (323, 373),
			"324A": (324, 374),
			"343B": (3430, 3450),
			"344A": (344, 394),
			"3440": (3440, 3940),
			"340": (3400, 3900),
			"338": (3380, 3880),
			"346B": (346, 396),
			"346D": (3370, 3870),
			"3480": (3480, 3980),
			"3482": (3140, 3640),
			"350": (350, 400),
			"336": (336, 386),
			"337": (337, 387),
			"505D": (402, 413),
			"505A": (403, 414, 424),
			"504E": (404, 415, 425),
			"504": (4050, 4160, 4260),
			"504A": (4060, 4170, 4270),
			"504B": (4070, 4180, 4280),
			"521": (408, 419, 429),
			"523A": (409, 420, 430),
			"501A": (410, 421, 431),
			"500": (411, 422, 432),
		}
		for code, expected in pairs.items():
			with self.subTest(code=code):
				self.assertEqual(casilleros_for(code), expected)

	def test_casilleros_for_singles_and_missing(self) -> None:
		for code, expected in (
			("309", (309,)),
			("310", (310,)),
			("332", (332,)),
			("333", (333,)),
			("335", (335,)),
		):
			with self.subTest(code=code):
				self.assertEqual(casilleros_for(code), expected)
		for code in ("325", "326", "343C", "502", "1", "344", "330"):
			with self.subTest(code=code):
				self.assertIsNone(casilleros_for(code))

	def test_casilleros_for_unknown_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			casilleros_for("344C")

	def test_concepto_rate_returns_rated_values(self) -> None:
		for code, expected in (("303", 10.0), ("312C", 1.75), ("325", 25.0), ("335", 15.0), ("332", 0.0)):
			with self.subTest(code=code):
				self.assertEqual(concepto_rate(code), expected)

	def test_concepto_rate_raises_for_unrated_and_unknown(self) -> None:
		for code in UNRATED:
			with self.subTest(code=code):
				_impuesto, rate, _description = resolve_concepto(code)
				self.assertIsNone(rate)
				with self.assertRaises(SriVoucherError):
					concepto_rate(code)
		with self.assertRaises(SriVoucherError):
			concepto_rate("999")

	def test_validate_concepto_map_rejects_non_emittable_exterior(self) -> None:
		with self.assertRaises(SriVoucherError):
			validate_concepto_map({"Ecuador exterior": ("9", "500")})
		with self.assertRaises(SriVoucherError):
			validate_concepto_map({"Ecuador exterior": ("1", "500")})

	def test_unmapped_codes_stay_out_but_documented(self) -> None:
		self.assertIn("344C", UNMAPPED_CONCEPTS)
		self.assertNotIn("344C", CONCEPTS)
		for code in ("401AA", "401PO", "401", "403", "405", "421", "427", "427A"):
			with self.subTest(code=code):
				self.assertIn(code, UNMAPPED_PRE2013_EXTERIOR)
				self.assertNotIn(code, CONCEPTS)
		self.assertTrue(UNMAPPED_PRE2013_EXTERIOR.isdisjoint(set(CONCEPTS)))


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

	def test_exterior_concepto_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			sustento_entries(self._row(), PURCHASE, {"Ecuador exterior": ("9", "500")})

	def test_missing_category_still_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			sustento_entries(self._row(), PURCHASE, {})
