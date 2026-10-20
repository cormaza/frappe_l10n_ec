from dataclasses import dataclass
from datetime import UTC, date, datetime, timezone
from random import randrange
from zoneinfo import ZoneInfo

import xmlsig
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import ExtensionNotFound
from cryptography.x509.oid import ExtensionOID, NameOID
from lxml import etree
from xades import XAdESContext, template
from xades.policy import ImpliedPolicy

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


ECUADOR_TZ = ZoneInfo("America/Guayaquil")


class SriSignatureError(ValueError):
	"""Raised when a PKCS#12 file cannot be decoded or fails validation."""


class SriSignatureExpiredError(SriSignatureError):
	"""Raised when attempting to sign an XML document with an expired certificate."""


@dataclass(frozen=True)
class CertificateMetadata:
	issue_date: date
	expire_date: date
	subject_common_name: str
	subject_serial_number: str
	issuer_common_name: str
	cert_serial_number: str
	cert_version: str
	state: str


def decode_certificate(
	file_content: bytes,
	password: str | bytes,
) -> tuple[RSAPrivateKey, x509.Certificate]:
	"""Decode a PKCS#12 signature bundle and select the certificate with digital_signature enabled.

	Ported from OCA/l10n-ecuador PR #102 (`sri_key_type.py::_decode_certificate`).
	When a PKCS#12 bundle contains multiple certificates (e.g. Banco Central del Ecuador or
	Security Data chains), selects the certificate whose KeyUsage extension has
	`digital_signature=True`.
	"""
	if not password:
		raise SriSignatureError(_("Signing password is required to decode the PKCS#12 file."))

	password_bytes = password.encode("utf-8") if isinstance(password, str) else password
	try:
		private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
			file_content, password_bytes
		)
	except Exception as ex:
		raise SriSignatureError(
			_(
				"Error opening the signature, possibly the signature key has been entered incorrectly or the file is not supported: {}"
			).format(ex)
		) from None

	if private_key is None or certificate is None:
		raise SriSignatureError(_("The PKCS#12 bundle does not contain a private key and certificate."))

	is_digital_signature = True
	try:
		extension = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
		is_digital_signature = bool(extension.value.digital_signature)
	except ExtensionNotFound:
		pass

	if not is_digital_signature:
		for other_cert in additional_certs or ():
			try:
				extension = other_cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
			except ExtensionNotFound:
				continue
			if extension.value.digital_signature:
				certificate = other_cert
				break

	return private_key, certificate


def get_certificate_date(
	cert: x509.Certificate,
	naive_attr: str,
	tz: ZoneInfo = ECUADOR_TZ,
) -> date:
	"""Return a certificate validity date in the target timezone (default America/Guayaquil).

	Ported from OCA/l10n-ecuador PR #102 (`sri_key_type.py::_l10n_ec_cert_date`).
	Uses `not_valid_before_utc` / `not_valid_after_utc` exposed by `cryptography >= 42`.
	"""
	aware_attr = f"{naive_attr}_utc"
	if hasattr(cert, aware_attr):
		aware_dt: datetime = getattr(cert, aware_attr)
		return aware_dt.astimezone(tz).date()
	naive_dt: datetime = getattr(cert, naive_attr)
	return naive_dt.replace(tzinfo=UTC).astimezone(tz).date()


def extract_certificate_metadata(
	file_content: bytes,
	password: str | bytes,
	today: date | None = None,
	tz: ZoneInfo = ECUADOR_TZ,
) -> CertificateMetadata:
	"""Validate a PKCS#12 file and extract X.509 subject/issuer/validity metadata.

	Ported from OCA/l10n-ecuador PR #102 (`sri_key_type.py::action_validate_and_load`).
	"""
	_private_key, cert = decode_certificate(file_content, password)
	issuer = cert.issuer
	subject = cert.subject

	subject_cn_attrs = subject.get_attributes_for_oid(NameOID.COMMON_NAME)
	subject_common_name = str(subject_cn_attrs[0].value) if subject_cn_attrs else ""

	subject_sn_attrs = subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)
	subject_serial_number = str(subject_sn_attrs[0].value) if subject_sn_attrs else ""

	issuer_cn_attrs = issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
	issuer_common_name = str(issuer_cn_attrs[0].value) if (subject_cn_attrs and issuer_cn_attrs) else ""

	issue_date = get_certificate_date(cert, "not_valid_before", tz=tz)
	expire_date = get_certificate_date(cert, "not_valid_after", tz=tz)
	reference_today = today or datetime.now(tz).date()
	state = "expired" if expire_date < reference_today else "valid"

	return CertificateMetadata(
		issue_date=issue_date,
		expire_date=expire_date,
		subject_common_name=subject_common_name,
		subject_serial_number=subject_serial_number,
		issuer_common_name=issuer_common_name,
		cert_serial_number=str(cert.serial_number),
		cert_version=str(cert.version),
		state=state,
	)


def sign_xml_xades_bes(
	xml_data: str | bytes,
	file_content: bytes,
	password: str | bytes,
	today: date | None = None,
	tz: ZoneInfo = ECUADOR_TZ,
) -> str:
	"""Sign an SRI electronic voucher XML with XAdES-BES (RSA-SHA1, Enveloped) and verify it.

	Ported from OCA/l10n-ecuador PR #102 (`sri_key_type.py::action_sign`).
	Directly assigns `ctx.x509`, `ctx.public_key`, and `ctx.private_key` instead of calling
	`ctx.load_pkcs12()`, which is broken on `pyOpenSSL >= 24` due to removal of
	`OpenSSL.crypto.PKCS12`.
	"""

	def new_range() -> int:
		return randrange(100000, 999999)

	private_key, cert = decode_certificate(file_content, password)
	expire_date = get_certificate_date(cert, "not_valid_after", tz=tz)
	reference_today = today or datetime.now(tz).date()
	if expire_date < reference_today:
		raise SriSignatureExpiredError(
			_(
				"The electronic signature expired on {} and the document cannot be signed. Upload a valid signature file in SRI Signature."
			).format(expire_date)
		)

	xml_bytes = xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data
	doc = etree.fromstring(xml_bytes)

	signature_id = f"Signature{new_range()}"
	signature_property_id = f"{signature_id}-SignedPropertiesID{new_range()}"
	certificate_id = f"Certificate{new_range()}"
	reference_uri = f"Reference-ID-{new_range()}"

	signature = xmlsig.template.create(
		xmlsig.constants.TransformInclC14N,
		xmlsig.constants.TransformRsaSha1,
		signature_id,
	)
	xmlsig.template.add_reference(
		signature,
		xmlsig.constants.TransformSha1,
		name=f"SignedPropertiesID{new_range()}",
		uri=f"#{signature_property_id}",
		uri_type="http://uri.etsi.org/01903#SignedProperties",
	)
	xmlsig.template.add_reference(
		signature,
		xmlsig.constants.TransformSha1,
		uri=f"#{certificate_id}",
	)
	ref = xmlsig.template.add_reference(
		signature,
		xmlsig.constants.TransformSha1,
		name=reference_uri,
		uri="#comprobante",
	)
	xmlsig.template.add_transform(ref, xmlsig.constants.TransformEnveloped)

	ki = xmlsig.template.ensure_key_info(signature, name=certificate_id)
	data = xmlsig.template.add_x509_data(ki)
	xmlsig.template.x509_data_add_certificate(data)
	xmlsig.template.add_key_value(ki)

	qualifying = template.create_qualifying_properties(signature, name=signature_id)
	props = template.create_signed_properties(qualifying, name=signature_property_id)
	signed_do = template.ensure_signed_data_object_properties(props)
	template.add_data_object_format(
		signed_do,
		f"#{reference_uri}",
		description="contenido comprobante",
		mime_type="text/xml",
	)
	doc.append(signature)

	ctx = XAdESContext(ImpliedPolicy(xmlsig.constants.TransformSha1))
	# Do not use ctx.load_pkcs12() here: xmlsig evaluates OpenSSL.crypto.PKCS12,
	# which pyOpenSSL >= 24 removed. Assigning the attributes directly matches
	# the tuple branch in xmlsig.SignatureContext.load_pkcs12.
	ctx.x509 = cert
	ctx.public_key = cert.public_key()
	ctx.private_key = private_key
	ctx.sign(signature)
	ctx.verify(signature)

	return etree.tostring(doc, encoding="UTF-8", pretty_print=True).decode("utf-8")
