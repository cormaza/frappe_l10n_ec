"""Unit tests for received SRI XML mapping (A1: upload/file core, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.received_invoice import map_received_factura
from l10n_ec.sri.voucher_data import parse_emitted_xml


def _factura_xml(lines_xml: str, emisor_ruc: str = "1790016919001") -> str:
	return f"""<factura id="comprobante" version="1.1.0">
<infoTributaria>
<ambiente>1</ambiente><tipoEmision>1</tipoEmision>
<razonSocial>PROVEEDOR EJEMPLO SA</razonSocial>
<nombreComercial>PROVEEDOR</nombreComercial>
<ruc>{emisor_ruc}</ruc>
<claveAcceso>2110202601179001691900110010010000000011234567818</claveAcceso>
<codDoc>01</codDoc><estab>001</estab><ptoEmi>001</ptoEmi><secuencial>000000001</secuencial>
<dirMatriz>Av. Amazonas</dirMatriz>
</infoTributaria>
<infoFactura>
<fechaEmision>20/10/2026</fechaEmision>
<dirEstablecimiento>Av. Shyris</dirEstablecimiento>
<obligadoContabilidad>SI</obligadoContabilidad>
<tipoIdentificacionComprador>04</tipoIdentificacionComprador>
<razonSocialComprador>DEMO ECUADOR SA</razonSocialComprador>
<identificacionComprador>1790016919001</identificacionComprador>
<totalSinImpuestos>1100.00</totalSinImpuestos>
<totalDescuento>0.00</totalDescuento>
<totalConImpuestos>
<totalImpuesto><codigo>2</codigo><codigoPorcentaje>4</codigoPorcentaje><baseImponible>1000.00</baseImponible><valor>150.00</valor></totalImpuesto>
<totalImpuesto><codigo>2</codigo><codigoPorcentaje>0</codigoPorcentaje><baseImponible>100.00</baseImponible><valor>0.00</valor></totalImpuesto>
</totalConImpuestos>
<propina>0.00</propina>
<importeTotal>1250.00</importeTotal>
<moneda>DOLAR</moneda>
</infoFactura>
<detalles>{lines_xml}</detalles>
</factura>"""


def _line(description: str, qty: str, price: str, total: str, taxes_xml: str = "") -> str:
	taxes = f"<impuestos>{taxes_xml}</impuestos>" if taxes_xml else ""
	return (
		f"<detalle><codigoPrincipal>WIDGET</codigoPrincipal>"
		f"<descripcion>{description}</descripcion>"
		f"<cantidad>{qty}</cantidad><precioUnitario>{price}</precioUnitario>"
		f"<descuento>0</descuento><precioTotalSinImpuesto>{total}</precioTotalSinImpuesto>"
		f"{taxes}</detalle>"
	)


def _tax(code: str, rate_code: str, rate: str, base: str, value: str) -> str:
	return (
		f"<impuesto><codigo>{code}</codigo><codigoPorcentaje>{rate_code}</codigoPorcentaje>"
		f"<tarifa>{rate}</tarifa><baseImponible>{base}</baseImponible><valor>{value}</valor></impuesto>"
	)


TEMPLATES = [
	{"title": "Ecuador VAT 15% - Purchases - DE", "rate": 15.0},
	{"title": "Ecuador VAT 0% - Purchases - DE", "rate": 0.0},
]


class TestParseEmisorAndLines(UnitTestCase):
	def test_emisor_and_clave_extracted(self) -> None:
		parsed = parse_emitted_xml(
			_factura_xml(_line("Widget A", "10", "100.00", "1000.00", _tax("2", "4", "15", "1000.00", "150.00")))
		)
		self.assertEqual(parsed["emisor_ruc"], "1790016919001")
		self.assertEqual(parsed["emisor_name"], "PROVEEDOR EJEMPLO SA")
		self.assertEqual(parsed["clave_acceso"], "2110202601179001691900110010010000000011234567818")

	def test_per_line_taxes_extracted(self) -> None:
		parsed = parse_emitted_xml(
			_factura_xml(_line("Widget A", "10", "100.00", "1000.00", _tax("2", "4", "15", "1000.00", "150.00")))
		)
		self.assertEqual(len(parsed["lines"]), 1)
		self.assertEqual(parsed["lines"][0]["taxes"][0]["rate_code"], "4")


class TestMapReceivedFactura(UnitTestCase):
	def _doc_kwargs(self, **overrides):
		base = {"item_code": "DEMO-WIDGET", "sustento": "01 - Con crédito tributario", "templates": TEMPLATES}
		base.update(overrides)
		return base

	def _parsed_two_rates(self):
		lines = _line("Widget A", "10", "100.00", "1000.00", _tax("2", "4", "15", "1000.00", "150.00"))
		lines += _line("Widget B", "2", "50.00", "100.00", _tax("2", "0", "0", "100.00", "0.00"))
		return parse_emitted_xml(_factura_xml(lines))

	def test_maps_supplier_number_date_and_auth(self) -> None:
		mapped = map_received_factura(self._parsed_two_rates(), **self._doc_kwargs())
		self.assertEqual(mapped["doctype"], "Purchase Invoice")
		self.assertEqual(mapped["supplier_tax_id"], "1790016919001")
		self.assertEqual(mapped["supplier_name"], "PROVEEDOR EJEMPLO SA")
		self.assertEqual(mapped["bill_no"], "001-001-000000001")
		self.assertEqual(mapped["bill_date"], "2026-10-20")
		self.assertEqual(mapped["sri_supplier_auth_number"], "2110202601179001691900110010010000000011234567818")

	def test_lines_carry_rate_matched_templates(self) -> None:
		mapped = map_received_factura(self._parsed_two_rates(), **self._doc_kwargs())
		rows = {row["description"]: row["item_tax_template"] for row in mapped["items"]}
		self.assertEqual(rows["Widget A"], "Ecuador VAT 15% - Purchases - DE")
		self.assertEqual(rows["Widget B"], "Ecuador VAT 0% - Purchases - DE")

	def test_unmapped_rate_fails_naming_it(self) -> None:
		with self.assertRaises(ValueError) as ctx:
			map_received_factura(
				self._parsed_two_rates(), **self._doc_kwargs(templates=[{"title": "T15", "rate": 15.0}])
			)
		self.assertIn("0", str(ctx.exception))

	def test_ambiguous_templates_fail(self) -> None:
		dupes = TEMPLATES + [{"title": "Other VAT 15%", "rate": 15.0}]
		with self.assertRaises(ValueError):
			map_received_factura(self._parsed_two_rates(), **self._doc_kwargs(templates=dupes))

	def test_missing_emisor_ruc_fails(self) -> None:
		parsed = parse_emitted_xml(
			_factura_xml(
				_line("Widget A", "1", "100.00", "100.00"),
				emisor_ruc="",
			)
		)
		with self.assertRaises(ValueError):
			map_received_factura(parsed, **self._doc_kwargs())

	def test_bad_date_fails(self) -> None:
		parsed = self._parsed_two_rates()
		parsed["issue_date"] = "2026-13-45"
		with self.assertRaises(ValueError):
			map_received_factura(parsed, **self._doc_kwargs())

	def test_unknown_currency_fails(self) -> None:
		parsed = self._parsed_two_rates()
		parsed["currency"] = "EUROS"
		with self.assertRaises(ValueError):
			map_received_factura(parsed, **self._doc_kwargs())
