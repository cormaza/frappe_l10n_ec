import unittest
from datetime import date

import xmlsig
from lxml import etree
from xades import XAdESContext
from xades.policy import ImpliedPolicy

from l10n_ec.sri.access_key import (
	clean_sri_string,
	compute_mod11_check_digit,
	generate_access_key,
	split_document_number,
)
from l10n_ec.sri.signer import (
	SriSignatureError,
	SriSignatureExpiredError,
	decode_certificate,
	extract_certificate_metadata,
	sign_xml_xades_bes,
)
from l10n_ec.tests.test_helpers import generate_test_p12

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

SAMPLE_INVOICE_XML = (
	b'<?xml version="1.0" encoding="UTF-8"?>'
	b'<factura id="comprobante" version="1.1.0">'
	b"<infoTributaria>"
	b"<ambiente>1</ambiente>"
	b"<tipoEmision>1</tipoEmision>"
	b"<razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>"
	b"<ruc>1790016919001</ruc>"
	b"<claveAcceso>2410202601179001691900110010010000000011234567815</claveAcceso>"
	b"<codDoc>01</codDoc>"
	b"<estab>001</estab>"
	b"<ptoEmi>001</ptoEmi>"
	b"<secuencial>000000001</secuencial>"
	b"<dirMatriz>Av. Amazonas y Naciones Unidas</dirMatriz>"
	b"</infoTributaria>"
	b"</factura>"
)


class TestSRISigner(UnitTestCase):
	"""Unit tests for SRI PKCS#12 decoding, XAdES-BES signing, and Modulo 11 access keys."""

	def test_valid_p12_decode_and_metadata(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=False)
		meta = extract_certificate_metadata(p12_bytes, "123456")
		self.assertEqual(meta.state, "valid")
		self.assertEqual(meta.subject_common_name, "SERVICIO DE RENTAS INTERNAS")
		self.assertEqual(meta.subject_serial_number, "1760013210001")
		self.assertEqual(meta.issuer_common_name, "SERVICIO DE RENTAS INTERNAS")
		self.assertGreater(meta.expire_date, meta.issue_date)

	def test_p12_without_key_usage_extension_falls_back_cleanly(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", include_key_usage=False)
		private_key, cert = decode_certificate(p12_bytes, "123456")
		self.assertIsNotNone(private_key)
		self.assertIsNotNone(cert)

	def test_multi_cert_p12_selects_digital_signature_from_additional_certs(self) -> None:
		p12_bytes = generate_test_p12(
			password=b"123456",
			expired=False,
			digital_signature_in_additional=True,
		)
		meta = extract_certificate_metadata(p12_bytes, "123456")
		self.assertEqual(meta.state, "valid")
		self.assertEqual(meta.subject_common_name, "SERVICIO DE RENTAS INTERNAS")
		self.assertEqual(meta.subject_serial_number, "1760013210001")

	def test_invalid_password_raises_sri_signature_error(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=False)
		with self.assertRaisesRegex(SriSignatureError, "Error opening the signature"):
			decode_certificate(p12_bytes, "wrong-password")

	def test_empty_password_raises_sri_signature_error(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=False)
		with self.assertRaisesRegex(SriSignatureError, "Signing password is required"):
			decode_certificate(p12_bytes, "")

	def test_expired_p12_blocks_signing(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=True)
		meta = extract_certificate_metadata(p12_bytes, "123456")
		self.assertEqual(meta.state, "expired")
		with self.assertRaisesRegex(SriSignatureExpiredError, "expired"):
			sign_xml_xades_bes(SAMPLE_INVOICE_XML, p12_bytes, "123456")

	def test_sign_and_verify_xades_bes_and_reject_tampering(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=False)
		signed_xml = sign_xml_xades_bes(SAMPLE_INVOICE_XML, p12_bytes, "123456")
		self.assertIn("<ds:Signature", signed_xml)
		self.assertIn("<etsi:QualifyingProperties", signed_xml)
		self.assertIn('URI="#comprobante"', signed_xml)

		# Verify that tampering with the signed XML invalidates the XAdES-BES signature
		tampered_xml = signed_xml.replace(
			"PRUEBAS SERVICIO DE RENTAS INTERNAS",
			"TAMPERED TAXPAYER NAME",
		)
		doc = etree.fromstring(tampered_xml.encode("utf-8"))
		sig_node = doc.xpath("//ds:Signature", namespaces={"ds": xmlsig.constants.DSigNs})[0]
		private_key, cert = decode_certificate(p12_bytes, "123456")
		ctx = XAdESContext(ImpliedPolicy(xmlsig.constants.TransformSha1))
		ctx.x509 = cert
		ctx.public_key = cert.public_key()
		ctx.private_key = private_key
		with self.assertRaises(Exception):
			ctx.verify(sig_node)

	def test_mod11_access_key_generation_and_check_digit(self) -> None:
		access_key = generate_access_key(
			document_code_sri="01",
			complete_document_number="001-001-000000001",
			environment="1",
			date_document=date(2026, 10, 24),
			ruc="1790016919001",
			numeric_code="12345678",
		)
		self.assertEqual(len(access_key), 49)
		self.assertTrue(access_key.isdigit())
		expected_check = compute_mod11_check_digit(access_key[:48])
		self.assertEqual(int(access_key[-1]), expected_check)

	def test_clean_sri_string_and_split_document_number(self) -> None:
		self.assertEqual(clean_sri_string("Compañía Áéíóú & Hijos #1!"), "Compania Aeiou  Hijos 1")
		self.assertEqual(split_document_number("1-2-45"), ("001", "002", "000000045"))
		with self.assertRaisesRegex(ValueError, "Invalid Ecuadorian document number"):
			split_document_number("001001000000045")
