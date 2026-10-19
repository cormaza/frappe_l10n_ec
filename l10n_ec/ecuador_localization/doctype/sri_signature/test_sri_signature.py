import base64
import unittest

from l10n_ec.ecuador_localization.doctype.sri_signature.sri_signature import SRISignature
from l10n_ec.sri.signer import SriSignatureExpiredError
from l10n_ec.tests.test_helpers import generate_test_p12

try:
	from frappe.tests import IntegrationTestCase, UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]
	IntegrationTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestSRISignatureUnit(UnitTestCase):
	"""Unit tests for the SRISignature DocType controller using Frappe v16 UnitTestCase."""

	def test_validate_and_sign_controller(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=False)
		doc = SRISignature(
			signature_name="Test Controller Key",
			p12_file="base64:" + base64.b64encode(p12_bytes).decode("ascii"),
			password="123456",
			_in_memory_test=True,
		)
		doc.validate()
		self.assertEqual(doc.state, "valid")
		self.assertEqual(doc.subject_common_name, "SERVICIO DE RENTAS INTERNAS")
		self.assertEqual(doc.subject_serial_number, "1760013210001")

		sample_xml = (
			b'<?xml version="1.0" encoding="UTF-8"?>'
			b'<factura id="comprobante" version="1.1.0"><infoTributaria/></factura>'
		)
		signed_xml = doc.sign_xml(sample_xml)
		self.assertIn("<ds:Signature", signed_xml)
		self.assertIn("<etsi:QualifyingProperties", signed_xml)

	def test_expired_signature_controller_blocks_signing(self) -> None:
		p12_bytes = generate_test_p12(password=b"123456", expired=True)
		doc = SRISignature(
			signature_name="Expired Controller Key",
			p12_file="base64:" + base64.b64encode(p12_bytes).decode("ascii"),
			password="123456",
			_in_memory_test=True,
		)
		doc.validate()
		self.assertEqual(doc.state, "expired")
		with self.assertRaises(Exception) as ctx:
			doc.sign_xml(b'<factura id="comprobante"/>')
		self.assertIn("expired", str(ctx.exception).lower())
