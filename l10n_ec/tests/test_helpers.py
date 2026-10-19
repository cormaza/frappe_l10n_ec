from datetime import UTC, datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def generate_test_p12(
	password: bytes = b"123456",
	expired: bool = False,
	digital_signature_in_additional: bool = False,
	include_key_usage: bool = True,
) -> bytes:
	"""Generate a self-signed PKCS#12 signature bundle for tests.

	Ported from OCA/l10n-ecuador PR #102 (`test_edi_common.py::_generate_test_p12`).
	Generating certificates dynamically relative to `datetime.now(timezone.utc)` ensures
	the test suite never suffers from calendar expiry of static `.p12` fixtures.
	"""
	key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	now = datetime.now(UTC)
	subject_name = x509.Name(
		[
			x509.NameAttribute(NameOID.COMMON_NAME, "SERVICIO DE RENTAS INTERNAS"),
			x509.NameAttribute(NameOID.SERIAL_NUMBER, "1760013210001"),
		]
	)

	def _build_cert(
		common_name: str,
		serial_str: str,
		digital_sig: bool,
		with_key_usage: bool = True,
	) -> x509.Certificate:
		name = x509.Name(
			[
				x509.NameAttribute(NameOID.COMMON_NAME, common_name),
				x509.NameAttribute(NameOID.SERIAL_NUMBER, serial_str),
			]
		)
		builder = (
			x509.CertificateBuilder()
			.subject_name(name)
			.issuer_name(subject_name)
			.public_key(key.public_key())
			.serial_number(x509.random_serial_number())
			.not_valid_before(now - timedelta(days=1))
			.not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=3650))
		)
		if with_key_usage:
			builder = builder.add_extension(
				x509.KeyUsage(
					digital_signature=digital_sig,
					content_commitment=False,
					key_encipherment=not digital_sig,
					data_encipherment=False,
					key_agreement=False,
					key_cert_sign=False,
					crl_sign=False,
					encipher_only=False,
					decipher_only=False,
				),
				critical=True,
			)
		return builder.sign(key, hashes.SHA256())

	if digital_signature_in_additional:
		primary_cert = _build_cert(
			"INTERMEDIATE ENCRYPTION CERT",
			"0000000000000",
			digital_sig=False,
			with_key_usage=True,
		)
		no_ext_cert = _build_cert(
			"NO EXTENSION CERT",
			"1111111111111",
			digital_sig=False,
			with_key_usage=False,
		)
		signing_cert = _build_cert(
			"SERVICIO DE RENTAS INTERNAS",
			"1760013210001",
			digital_sig=True,
			with_key_usage=True,
		)
		additional_certs = [no_ext_cert, signing_cert]
	else:
		primary_cert = _build_cert(
			"SERVICIO DE RENTAS INTERNAS",
			"1760013210001",
			digital_sig=True,
			with_key_usage=include_key_usage,
		)
		additional_certs = None

	return pkcs12.serialize_key_and_certificates(
		b"test",
		key,
		primary_cert,
		additional_certs,
		serialization.BestAvailableEncryption(password),
	)
