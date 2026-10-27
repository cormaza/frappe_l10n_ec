"""Unit tests for received retencion mapping (T4: customer withholding XML)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.received_retention import map_received_retencion
from l10n_ec.sri.voucher_data import parse_emitted_xml

COMPROBANTE_XML = """<comprobanteRetencion id="comprobante" version="1.0.0">
<infoTributaria>
<ambiente>1</ambiente><tipoEmision>1</tipoEmision>
<razonSocial>CLIENTE EJEMPLO SA</razonSocial>
<nombreComercial>CLIENTE</nombreComercial>
<ruc>1790016919001</ruc>
<claveAcceso>2410202601179001691900110010010000001011234567815</claveAcceso>
<codDoc>07</codDoc><estab>001</estab><ptoEmi>001</ptoEmi><secuencial>000000101</secuencial>
<dirMatriz>Av. Amazonas</dirMatriz>
</infoTributaria>
<infoCompRetencion>
<fechaEmision>20/10/2026</fechaEmision>
<dirEstablecimiento>Av. Shyris</dirEstablecimiento>
<contribuyenteEspecial>12345</contribuyenteEspecial>
<obligadoContabilidad>SI</obligadoContabilidad>
<tipoIdentificacionSujetoRetenido>04</tipoIdentificacionSujetoRetenido>
<razonSocialSujetoRetenido>DEMO ECUADOR SA</razonSocialSujetoRetenido>
<identificacionSujetoRetenido>1760013219001</identificacionSujetoRetenido>
<periodoFiscal>10/2026</periodoFiscal>
</infoCompRetencion>
<docsSustento>
<docSustento>
<codDocSustento>01</codDocSustento>
<numDocSustento>001-002-000000009</numDocSustento>
<fechaEmisionDocSustento>15/10/2026</fechaEmisionDocSustento>
<fechaRegistroContable>15/10/2026</fechaRegistroContable>
<numAutDocSustento>1234567890</numAutDocSustento>
<pagoLocExt>01</pagoLocExt>
<totalSinImpuestos>900.00</totalSinImpuestos>
<importeTotal>1017.00</importeTotal>
<impuestosDocSustento><impuestoDocSustento><codImpuesto>2</codImpuesto><codigoPorcentaje>4</codigoPorcentaje><baseImponible>900.00</baseImponible><tarifa>15</tarifa><valorImpuesto>135.00</valorImpuesto></impuestoDocSustento></impuestosDocSustento>
<retenciones><retencion>
<codigo>303</codigo><codigoRetencion>303</codigoRetencion><baseImponible>900.00</baseImponible><porcentajeRetener>10</porcentajeRetener><valorRetenido>90.00</valorRetenido>
</retencion></retenciones>
</docSustento>
</docsSustento>
</comprobanteRetencion>"""


class TestParseRetencionEmisor(UnitTestCase):
	def test_emisor_clave_extracted(self) -> None:
		parsed = parse_emitted_xml(COMPROBANTE_XML)
		self.assertEqual(parsed["emisor_ruc"], "1790016919001")
		self.assertEqual(parsed["emisor_name"], "CLIENTE EJEMPLO SA")
		self.assertEqual(parsed["clave_acceso"], "2410202601179001691900110010010000001011234567815")


class TestMapReceivedRetencion(UnitTestCase):
	def test_maps_customer_and_allocations(self) -> None:
		parsed = parse_emitted_xml(COMPROBANTE_XML)
		mapped = map_received_retencion(parsed)
		self.assertEqual(mapped["customer_tax_id"], "1790016919001")
		self.assertEqual(mapped["retencion_number"], "001-001-000000101")
		self.assertEqual(mapped["authorization"], "2410202601179001691900110010010000001011234567815")
		self.assertEqual(len(mapped["allocations"]), 1)
		alloc = mapped["allocations"][0]
		self.assertEqual(alloc["doc_number"], "001-002-000000009")
		self.assertEqual(alloc["ir_value"], 90.0)
		self.assertEqual(alloc["iva_value"], 0.0)

	def test_missing_emisor_fails(self) -> None:
		parsed = parse_emitted_xml(COMPROBANTE_XML.replace("<ruc>1790016919001</ruc>", "<ruc></ruc>"))
		with self.assertRaises(ValueError):
			map_received_retencion(parsed)

	def test_rate_mismatch_fails_naming_concepto(self) -> None:
		parsed = parse_emitted_xml(COMPROBANTE_XML.replace("<porcentajeRetener>10</porcentajeRetener>", "<porcentajeRetener>8</porcentajeRetener>"))
		with self.assertRaises(ValueError) as ctx:
			map_received_retencion(parsed)
		self.assertIn("303", str(ctx.exception))

	def test_exterior_concepto_fails_loud(self) -> None:
		parsed = parse_emitted_xml(
			COMPROBANTE_XML.replace("<codigo>303</codigo><codigoRetencion>303</codigoRetencion>", "<codigo>1</codigo><codigoRetencion>501A</codigoRetencion>")
		)
		with self.assertRaises(ValueError):
			map_received_retencion(parsed)
