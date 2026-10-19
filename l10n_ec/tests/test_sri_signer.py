from datetime import date

import pytest
import xmlsig
from lxml import etree
from xades import XAdESContext
from xades.policy import ImpliedPolicy

from l10n_ec.ecuador_localization.doctype.sri_signature.test_sri_signature import (
	TestSRISignatureUnit,
)
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


def test_valid_p12_decode_and_metadata() -> None:
	p12_bytes = generate_test_p12(password=b"123456", expired=False)
	meta = extract_certificate_metadata(p12_bytes, "123456")
	assert meta.state == "valid"
	assert meta.subject_common_name == "SERVICIO DE RENTAS INTERNAS"
	assert meta.subject_serial_number == "1760013210001"
	assert meta.issuer_common_name == "SERVICIO DE RENTAS INTERNAS"
	assert meta.expire_date > meta.issue_date


def test_p12_without_key_usage_extension_falls_back_cleanly() -> None:
	p12_bytes = generate_test_p12(password=b"123456", include_key_usage=False)
	private_key, cert = decode_certificate(p12_bytes, "123456")
	assert private_key is not None
	assert cert is not None


def test_multi_cert_p12_selects_digital_signature_from_additional_certs() -> None:
	p12_bytes = generate_test_p12(
		password=b"123456",
		expired=False,
		digital_signature_in_additional=True,
	)
	meta = extract_certificate_metadata(p12_bytes, "123456")
	assert meta.state == "valid"
	assert meta.subject_common_name == "SERVICIO DE RENTAS INTERNAS"
	assert meta.subject_serial_number == "1760013210001"


def test_invalid_password_raises_sri_signature_error() -> None:
	p12_bytes = generate_test_p12(password=b"123456", expired=False)
	with pytest.raises(SriSignatureError, match="Error opening the signature"):
		decode_certificate(p12_bytes, "wrong-password")


def test_empty_password_raises_sri_signature_error() -> None:
	p12_bytes = generate_test_p12(password=b"123456", expired=False)
	with pytest.raises(SriSignatureError, match="Signing password is required"):
		decode_certificate(p12_bytes, "")


def test_expired_p12_blocks_signing() -> None:
	p12_bytes = generate_test_p12(password=b"123456", expired=True)
	meta = extract_certificate_metadata(p12_bytes, "123456")
	assert meta.state == "expired"
	with pytest.raises(SriSignatureExpiredError, match="expired"):
		sign_xml_xades_bes(SAMPLE_INVOICE_XML, p12_bytes, "123456")


def test_sign_and_verify_xades_bes_and_reject_tampering() -> None:
	p12_bytes = generate_test_p12(password=b"123456", expired=False)
	signed_xml = sign_xml_xades_bes(SAMPLE_INVOICE_XML, p12_bytes, "123456")
	assert "<ds:Signature" in signed_xml
	assert "<etsi:QualifyingProperties" in signed_xml
	assert 'URI="#comprobante"' in signed_xml

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
	with pytest.raises(Exception):
		ctx.verify(sig_node)


def test_mod11_access_key_generation_and_check_digit() -> None:
	access_key = generate_access_key(
		document_code_sri="01",
		complete_document_number="001-001-000000001",
		environment="1",
		date_document=date(2026, 10, 24),
		ruc="1790016919001",
		numeric_code="12345678",
	)
	assert len(access_key) == 49
	assert access_key.isdigit()
	expected_check = compute_mod11_check_digit(access_key[:48])
	assert int(access_key[-1]) == expected_check


def test_clean_sri_string_and_split_document_number() -> None:
	assert clean_sri_string("Compañía Áéíóú & Hijos #1!") == "Compania Aeiou  Hijos 1"
	assert split_document_number("1-2-45") == ("001", "002", "000000045")
	with pytest.raises(ValueError, match="Invalid Ecuadorian document number"):
		split_document_number("001001000000045")


def test_doctype_controller_unit_suite() -> None:
	suite = TestSRISignatureUnit()
	suite.test_validate_and_sign_controller()
	suite.test_expired_signature_controller_blocks_signing()
