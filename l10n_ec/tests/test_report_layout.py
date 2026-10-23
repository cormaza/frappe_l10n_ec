"""Unit tests for SRI report layouts (pure, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.ats_layout import build_ats_rows
from l10n_ec.sri.form103 import build_103_rows
from l10n_ec.sri.form104_layout import BLOCK_TITLES, build_104_rows, label_for


class TestForm104Layout(UnitTestCase):
	def test_triplet_row_carries_dimm_labels_and_values(self) -> None:
		totals = {"401": 1500.0, "411": 1500.0, "421": 225.0, "409": 1500.0, "419": 1500.0, "429": 225.0}
		rows = build_104_rows(totals)
		first = next(r for r in rows if r["kind"] == "triplet")
		self.assertIn("401", first["casilleros"])
		self.assertIn("VENTAS LOCALES", first["descripcion"])
		self.assertEqual(first["bruto"], 1500.0)
		self.assertEqual(first["neto"], 1500.0)
		self.assertEqual(first["impuesto"], 225.0)
		self.assertEqual(first["signo"], "+")

	def test_blocks_follow_dimm_order(self) -> None:
		rows = build_104_rows({"401": 1.0, "500": 2.0, "601": 3.0, "721": 4.0, "859": 5.0})
		sections = [r["descripcion"] for r in rows if r["kind"] == "section"]
		self.assertEqual(sections, list(BLOCK_TITLES))

	def test_label_for_known_box(self) -> None:
		self.assertIn("GRAVADAS TARIFA DIFERENTE DE CERO", label_for("401"))
		self.assertIn("RISE", label_for("508"))
		self.assertIn("RETENCIÓN DEL 30%", label_for("725"))

	def test_unexpected_nonzero_box_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			build_104_rows({"486": 10.0})

	def test_signo_marks_minus_and_total_boxes(self) -> None:
		rows = build_104_rows({"424": 5.0, "409": 1.0, "419": 1.0, "429": 1.0, "620": -2.0})
		by_box = {r["casilleros"]: r for r in rows if r["kind"] != "section"}
		self.assertEqual(by_box["424"]["signo"], "-")
		self.assertEqual(by_box["409 · 419 · 429"]["signo"], "=")
		self.assertEqual(by_box["620"]["signo"], "=")
		self.assertEqual(by_box["620"]["neto"], -2.0)


class TestForm103Rows(UnitTestCase):
	def test_concepto_row_shows_code_description_and_boxes(self) -> None:
		rows = build_103_rows({312: 100.0, 362: 2.0}, {"312": {"base": 100.0, "value": 2.0}})
		concepto = next(r for r in rows if r["kind"] == "concepto")
		self.assertIn("312", concepto["concepto"])
		self.assertIn("Bienes", concepto["concepto"])
		self.assertEqual(concepto["cas_base"], 312)
		self.assertEqual(concepto["base"], 100.0)
		self.assertEqual(concepto["cas_impuesto"], 362)
		self.assertEqual(concepto["impuesto"], 2.0)

	def test_total_row_sums_residentes(self) -> None:
		rows = build_103_rows(
			{312: 100.0, 362: 2.0, 303: 50.0, 353: 5.0},
			{"312": {"base": 100.0, "value": 2.0}, "303": {"base": 50.0, "value": 5.0}},
		)
		total = next(r for r in rows if r["kind"] == "total")
		self.assertEqual(total["base"], 150.0)
		self.assertEqual(total["impuesto"], 7.0)

	def test_unattributable_casillero_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			build_103_rows({99999: 1.0}, {})

	def test_shared_box_renders_fired_concepto_once(self) -> None:
		rows = build_103_rows({332: 500.0}, {"332": {"base": 500.0, "value": 0.0}})
		conceptos = [r for r in rows if r["kind"] == "concepto"]
		self.assertEqual(len(conceptos), 1)
		self.assertTrue(conceptos[0]["concepto"].startswith("332 —"))

	def test_totals_without_detail_fail_loud(self) -> None:
		with self.assertRaises(ValueError):
			build_103_rows({312: 100.0, 362: 2.0})

	def test_negative_value_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			build_103_rows({312: -100.0, 362: -2.0})


class TestAtsLayout(UnitTestCase):
	def test_compra_detail_and_subtotal(self) -> None:
		collected = {
			"compras": [
				{
					"codSustento": "02",
					"tpIdProv": "04",
					"idProv": "1710034065001",
					"tipoComprobante": "01",
					"denoProv": "Demo Supplier RUC",
					"establecimiento": "001",
					"puntoEmision": "001",
					"secuencial": "000000014",
					"autorizacion": "1234567890",
					"baseImpGrav": 200.0,
					"montoIva": 30.0,
				}
			],
			"ventas": [],
			"exportaciones": [],
			"anulados": [],
		}
		rows = build_ats_rows(collected)
		detail = next(r for r in rows if r["kind"] == "detail")
		self.assertIn("000000014", detail["comprobante"])
		self.assertIn("Demo Supplier", detail["tercero"])
		subtotal = next(r for r in rows if r["kind"] == "subtotal")
		self.assertEqual(subtotal["base"], 200.0)
		self.assertEqual(subtotal["iva"], 30.0)
