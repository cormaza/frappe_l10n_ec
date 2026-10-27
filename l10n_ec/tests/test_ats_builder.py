"""Unit tests for the ATS XML renderer and month zip (pure parts, no frappe)."""

import io
import unittest
import zipfile

from l10n_ec.sri.ats_builder import (
	ats_filename,
	build_ats_xml,
	build_ats_zip,
)
from l10n_ec.sri.xml_builder import SriXmlError, validate_against_xsd

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


INFORMANTE = {
	"IdInformante": "1790016919001",
	"razonSocial": "DEMO COMPANY SA",
}


def _compra(**overrides):
	row = {
		"codSustento": "02",
		"tpIdProv": "04",
		"idProv": "1790016919001",
		"tipoComprobante": "01",
		"denoProv": "Demo Supplier",
		"parteRel": "NO",
		"fechaRegistro": "20/03/2026",
		"establecimiento": "001",
		"puntoEmision": "001",
		"secuencial": "000000123",
		"fechaEmision": "15/03/2026",
		"autorizacion": "1234567890",
		"baseNoGraIva": 0.0,
		"baseImponible": 0.0,
		"baseImpGrav": 1000.0,
		"baseImpExe": 0.0,
		"montoIce": 12.5,
		"montoIva": 150.0,
		"valRetBien10": 0.0,
		"valRetServ20": 0.0,
		"valorRetBienes": 0.0,
		"valRetServ50": 0.0,
		"valorRetServicios": 105.0,
		"valRetServ100": 0.0,
		"formasDePago": ["01"],
		"air": [
			{
				"codRetAir": "303",
				"baseImpAir": 1000.0,
				"porcentajeAir": 10.0,
				"valRetAir": 100.0,
			}
		],
		"estabRetencion1": "001",
		"ptoEmiRetencion1": "001",
		"secRetencion1": "000000007",
		"autRetencion1": "1234567890",
		"fechaEmiRet1": "25/03/2026",
	}
	row.update(overrides)
	return row


def _venta(**overrides):
	row = {
		"tpIdCliente": "04",
		"idCliente": "1790016919001",
		"denoCli": "Demo Customer",
		"tipoComprobante": "01",
		"tipoEmision": "E",
		"numeroComprobantes": 1,
		"baseNoGraIva": 0.0,
		"baseImponible": 0.0,
		"baseImpGrav": 1000.0,
		"montoIva": 150.0,
		"montoIce": 0.0,
		"valorRetIva": 45.0,
		"valorRetRenta": 20.0,
		"formasDePago": ["19"],
		"received_number": "001-002-000000009",
		"received_authorization": "0987654321",
		"received_date": "28/03/2026",
		"received_access_key": "1" * 49,
	}
	row.update(overrides)
	return row


def _exportacion(**overrides):
	row = {
		"exportacionDe": "01",
		"tipoComprobante": "01",
		"fechaEmbarque": "16/03/2026",
		"valorFOB": 5000.0,
		"valorFOBComprobante": 5000.0,
		"establecimiento": "001",
		"puntoEmision": "001",
		"secuencial": "000000400",
		"autorizacion": "1234567890",
		"fechaEmision": "15/03/2026",
	}
	row.update(overrides)
	return row


def _anulado(**overrides):
	row = {
		"tipoComprobante": "01",
		"establecimiento": "001",
		"puntoEmision": "001",
		"secuencialInicio": "000000124",
		"secuencialFin": "000000124",
		"autorizacion": "1234567890",
	}
	row.update(overrides)
	return row


def _collected(**overrides):
	payload = {
		"informante": dict(INFORMANTE),
		"compras": [_compra()],
		"ventas": [_venta()],
		"exportaciones": [_exportacion()],
		"anulados": [_anulado()],
	}
	payload.update(overrides)
	return payload


class TestBuildAtsXml(UnitTestCase):
	def test_full_month_validates_against_xsd(self) -> None:
		xml = build_ats_xml(_collected(), "032026")
		self.assertTrue(validate_against_xsd(xml, "ats"))
		for tag in (
			"<TipoIDInformante>R</TipoIDInformante>",
			"<IdInformante>1790016919001</IdInformante>",
			"<Anio>2026</Anio>",
			"<Mes>03</Mes>",
			"<codigoOperativo>IVA</codigoOperativo>",
			"<detalleCompras>",
			"<detalleVentas>",
			"<detalleExportaciones>",
			"<detalleAnulados>",
		):
			self.assertIn(tag, xml)

	def test_ice_row_and_withholdings_render(self) -> None:
		xml = build_ats_xml(_collected(), "03/2026")
		self.assertIn("<montoIce>12.50</montoIce>", xml)
		self.assertIn("<codRetAir>303</codRetAir>", xml)
		self.assertIn("<valorRetServicios>105.00</valorRetServicios>", xml)
		self.assertIn("<secRetencion1>000000007</secRetencion1>", xml)
		self.assertIn("<formaPago>01</formaPago>", xml)

	def test_received_credit_flows_to_ventas(self) -> None:
		xml = build_ats_xml(_collected(), "2026-03")
		self.assertIn("<valorRetIva>45.00</valorRetIva>", xml)
		self.assertIn("<valorRetRenta>20.00</valorRetRenta>", xml)
		self.assertNotIn("received_number", xml)
		self.assertNotIn("1" * 49, xml)

	def test_export_and_anulado_rows_render(self) -> None:
		xml = build_ats_xml(_collected(), "032026")
		self.assertIn("<exportacionDe>01</exportacionDe>", xml)
		self.assertIn("<valorFOB>5000.00</valorFOB>", xml)
		self.assertIn("<fechaEmbarque>16/03/2026</fechaEmbarque>", xml)
		self.assertIn("<secuencialInicio>000000124</secuencialInicio>", xml)
		self.assertIn("<secuencialFin>000000124</secuencialFin>", xml)

	def test_optional_buckets_render_in_schema_order(self) -> None:
		xml = build_ats_xml(_collected(compras=[_compra(valRetBien10=3.0, valRetServ50=7.0)]), "032026")
		self.assertTrue(validate_against_xsd(xml, "ats"))
		positions = [
			xml.index(f"<{tag}>")
			for tag in ("valRetBien10", "valorRetBienes", "valRetServ50", "valorRetServicios")
		]
		self.assertEqual(positions, sorted(positions))

	def test_zero_optional_buckets_are_omitted(self) -> None:
		xml = build_ats_xml(_collected(), "032026")
		self.assertTrue(validate_against_xsd(xml, "ats"))
		for tag in ("<valRetBien10>", "<valRetServ20>", "<valRetServ50>"):
			self.assertNotIn(tag, xml)

	def test_sections_follow_xsd_element_order(self) -> None:
		xml = build_ats_xml(_collected(), "032026")
		positions = [
			xml.index(f"<{tag}>")
			for tag in (
				"TipoIDInformante",
				"IdInformante",
				"razonSocial",
				"Anio",
				"Mes",
				"codigoOperativo",
				"compras",
				"ventas",
				"exportaciones",
				"anulados",
			)
		]
		self.assertEqual(positions, sorted(positions))

	def test_empty_month_validates_without_detail_rows(self) -> None:
		xml = build_ats_xml(
			{
				"informante": dict(INFORMANTE),
				"compras": [],
				"ventas": [],
				"exportaciones": [],
				"anulados": [],
			},
			"032026",
		)
		self.assertTrue(validate_against_xsd(xml, "ats"))
		for detail in (
			"<detalleCompras>",
			"<detalleVentas>",
			"<detalleExportaciones>",
			"<detalleAnulados>",
		):
			self.assertNotIn(detail, xml)

	def test_header_alias_is_accepted(self) -> None:
		payload = _collected()
		payload["header"] = payload.pop("informante")
		xml = build_ats_xml(payload, "032026")
		self.assertTrue(validate_against_xsd(xml, "ats"))

	def test_missing_monto_ice_on_compras_raises(self) -> None:
		row = _compra()
		del row["montoIce"]
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(compras=[row]), "032026")

	def test_unknown_field_raises(self) -> None:
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(compras=[_compra(mystery="1")]), "032026")

	def test_unknown_section_raises(self) -> None:
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(recap=[]), "032026")

	def test_partial_withholding_reference_raises(self) -> None:
		row = _compra()
		del row["autRetencion1"]
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(compras=[row]), "032026")

	def test_bad_period_raises(self) -> None:
		for period in ("", "2026", "132026", "03/1999", "nope"):
			with self.subTest(period=period):
				with self.assertRaises(SriXmlError):
					build_ats_xml(_collected(), period)

	def test_missing_informante_raises(self) -> None:
		with self.assertRaises(SriXmlError):
			build_ats_xml({"compras": [], "ventas": [], "exportaciones": [], "anulados": []}, "032026")

	def test_schema_rejects_invalid_values(self) -> None:
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(compras=[_compra(autorizacion="AB")]), "032026")


class TestCompraReembolso(UnitTestCase):
	"""T3 (S2): totbasesImpReemb plus reembolsos render in XSD order."""

	def _reembolso_row(self, **overrides):
		row = {
			"tipoComprobanteReemb": "01",
			"tpIdProvReemb": "04",
			"idProvReemb": "1790016919001",
			"establecimientoReemb": "001",
			"puntoEmisionReemb": "001",
			"secuencialReemb": "000000010",
			"fechaEmisionReemb": "15/03/2026",
			"autorizacionReemb": "1234567890",
			"baseImponibleReemb": 100.0,
			"baseImpGravReemb": 50.0,
			"baseNoGraIvaReemb": 10.0,
			"baseImpExeReemb": 5.0,
			"montoIceRemb": 1.0,
			"montoIvaRemb": 7.5,
		}
		row.update(overrides)
		return row

	def test_reembolso_block_renders_in_schema_order(self) -> None:
		xml = build_ats_xml(
			_collected(compras=[_compra(totbasesImpReemb=150.0, reembolsos=[self._reembolso_row()])]),
			"032026",
		)
		self.assertTrue(validate_against_xsd(xml, "ats"))
		self.assertIn("<totbasesImpReemb>150.00</totbasesImpReemb>", xml)
		self.assertIn("<reembolsos><reembolso>", xml)
		self.assertIn("<tipoComprobanteReemb>01</tipoComprobanteReemb>", xml)
		positions = [xml.index(f"<{tag}>") for tag in ("totbasesImpReemb", "formasDePago", "reembolsos")]
		self.assertEqual(positions, sorted(positions))
		inner = xml[xml.index("<reembolso>") : xml.index("</reembolso>")]
		order = [
			"tipoComprobanteReemb",
			"tpIdProvReemb",
			"idProvReemb",
			"establecimientoReemb",
			"puntoEmisionReemb",
			"secuencialReemb",
			"fechaEmisionReemb",
			"autorizacionReemb",
			"baseImponibleReemb",
			"baseImpGravReemb",
			"baseNoGraIvaReemb",
			"baseImpExeReemb",
			"montoIceRemb",
			"montoIvaRemb",
		]
		inner_positions = [inner.index(f"<{tag}>") for tag in order]
		self.assertEqual(inner_positions, sorted(inner_positions))

	def test_partial_reembolso_fails_loud(self) -> None:
		bad = self._reembolso_row()
		del bad["autorizacionReemb"]
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(compras=[_compra(reembolsos=[bad])]), "032026")

	def test_reembolsos_without_total_fails_loud(self) -> None:
		with self.assertRaises(SriXmlError):
			build_ats_xml(_collected(compras=[_compra(reembolsos=[self._reembolso_row()])]), "032026")


class TestBuildAtsZip(UnitTestCase):
	def test_zip_holds_single_month_file(self) -> None:
		xml = build_ats_xml(_collected(), "032026")
		data = build_ats_zip(xml, "032026")
		with zipfile.ZipFile(io.BytesIO(data)) as archive:
			self.assertEqual(archive.namelist(), ["AT032026.xml"])
			self.assertEqual(archive.read("AT032026.xml").decode("utf-8"), xml)

	def test_zip_filename_follows_period(self) -> None:
		xml = build_ats_xml(_collected(), "032026")
		data = build_ats_zip(xml, "03/2026")
		with zipfile.ZipFile(io.BytesIO(data)) as archive:
			self.assertEqual(archive.namelist(), ["AT032026.xml"])

	def test_ats_filename(self) -> None:
		self.assertEqual(ats_filename("032026"), "AT032026.xml")
		self.assertEqual(ats_filename("2026-03"), "AT032026.xml")
		with self.assertRaises(SriXmlError):
			ats_filename("nope")

	def test_zip_rejects_invalid_xml(self) -> None:
		with self.assertRaises(SriXmlError):
			build_ats_zip("<iva/>", "032026")
		with self.assertRaises(SriXmlError):
			build_ats_zip("", "032026")


if __name__ == "__main__":
	unittest.main()
