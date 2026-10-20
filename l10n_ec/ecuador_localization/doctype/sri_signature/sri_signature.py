from __future__ import annotations

import base64
from datetime import date
from typing import TYPE_CHECKING

from l10n_ec.sri.signer import (
	SriSignatureError,
	extract_certificate_metadata,
	sign_xml_xades_bes,
)

try:
	import frappe
	from frappe import _
	from frappe.model.document import Document
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message

	class Document:  # type: ignore[no-redef]
		"""Fallback base class when imported outside a Frappe Bench environment."""

		def __init__(self, *args, **kwargs):
			for key, value in kwargs.items():
				setattr(self, key, value)

	frappe = None  # type: ignore[assignment]


class SRISignature(Document):
	"""Frappe v16 DocType controller for Ecuadorian SRI PKCS#12 electronic signatures.

	Equivalent to `sri.key.type` in OCA/l10n-ecuador PR #102.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		cert_serial_number: DF.Data | None
		cert_version: DF.Data | None
		company: DF.Link | None
		days_for_notification: DF.Int
		expire_date: DF.Date | None
		issuer_common_name: DF.Data | None
		not_valid_before: DF.Date | None
		p12_file: DF.Attach
		password: DF.Password
		signature_name: DF.Data
		state: DF.Literal["unverified", "valid", "expired"]
		subject_common_name: DF.Data | None
		subject_serial_number: DF.Data | None

	def validate(self) -> None:
		if getattr(self, "p12_file", None) and self._get_signing_password():
			self.action_validate_and_load()

	def _get_signing_password(self) -> str:
		if frappe and hasattr(self, "get_password") and not getattr(self, "_in_memory_test", False):
			try:
				return self.get_password("password")
			except Exception:
				pass
		return getattr(self, "password", "") or ""

	def _get_p12_bytes(self) -> bytes:
		raw_bytes = getattr(self, "_p12_bytes", None)
		if raw_bytes:
			return raw_bytes

		p12_file = getattr(self, "p12_file", None)
		if isinstance(p12_file, bytes):
			return p12_file
		if isinstance(p12_file, str) and p12_file.startswith("base64:"):
			return base64.b64decode(p12_file.removeprefix("base64:"))
		if frappe and p12_file:
			file_doc = frappe.get_doc("File", {"file_url": p12_file})
			content = file_doc.get_content()
			return content.encode("utf-8") if isinstance(content, str) else content

		raise SriSignatureError(_("No PKCS#12 signature content attached to SRI Signature document."))

	def action_validate_and_load(self, today: date | None = None) -> bool:
		"""Decode PKCS#12 signature, populate certificate metadata fields, and update state."""
		try:
			metadata = extract_certificate_metadata(
				file_content=self._get_p12_bytes(),
				password=self._get_signing_password(),
				today=today,
			)
		except SriSignatureError as exc:
			if frappe:
				frappe.throw(str(exc))
			raise

		self.not_valid_before = metadata.issue_date
		self.expire_date = metadata.expire_date
		self.subject_common_name = metadata.subject_common_name
		self.subject_serial_number = metadata.subject_serial_number
		self.issuer_common_name = metadata.issuer_common_name
		self.cert_serial_number = metadata.cert_serial_number
		self.cert_version = metadata.cert_version
		self.state = metadata.state
		return True

	def sign_xml(self, xml_string: str | bytes, today: date | None = None) -> str:
		"""Sign an SRI XML voucher with XAdES-BES and verify the resulting signature."""
		try:
			return sign_xml_xades_bes(
				xml_data=xml_string,
				file_content=self._get_p12_bytes(),
				password=self._get_signing_password(),
				today=today,
			)
		except SriSignatureError as exc:
			if frappe:
				frappe.throw(str(exc))
			raise

	def days_to_expire(self, today: date | None = None) -> int:
		if not getattr(self, "expire_date", None):
			return 0
		reference_today = today or date.today()
		return (self.expire_date - reference_today).days
