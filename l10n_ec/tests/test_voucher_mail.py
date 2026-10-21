import unittest
from types import SimpleNamespace

import l10n_ec.ecuador_localization.voucher_mail as voucher_mail
from l10n_ec.ecuador_localization.voucher_mail import (
	authorized_mail_subject,
	build_attachments,
	resolve_recipients,
	ride_print_format,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class _FakeDB:
	"""Minimal `frappe.db` stand-in keyed by `(doctype, name, field)`."""

	def __init__(self, values: dict) -> None:
		self._values = values

	def get_value(self, doctype: str, name_or_filters, field=None, as_dict=False):
		if isinstance(name_or_filters, dict):
			key = tuple(sorted(name_or_filters.items()))
		else:
			key = name_or_filters
		return self._values.get((doctype, key, field))


class _FakeFrappe:
	"""Minimal `frappe` stand-in capturing `sendmail` calls."""

	def __init__(self, docs: dict, values: dict) -> None:
		self._docs = docs
		self.db = _FakeDB(values)
		self.sent: list = []

	def get_doc(self, doctype: str, name: str):
		return self._docs[(doctype, name)]

	def sendmail(self, **kwargs):
		self.sent.append(kwargs)
		return kwargs


def _sri_number(code: str) -> str:
	return f"001-001-000000001-{code}"


class TestVoucherMail(UnitTestCase):
	"""Unit tests for authorized-voucher email composition (pure Python)."""

	def test_recipients_prefer_customer_email(self) -> None:
		self.assertEqual(resolve_recipients("c@example.com", "p@example.com"), ["c@example.com"])
		self.assertEqual(resolve_recipients("", "p@example.com"), ["p@example.com"])
		self.assertEqual(resolve_recipients(None, None), [])

	def test_subject_carries_access_key(self) -> None:
		subject = authorized_mail_subject("123")
		self.assertIn("123", subject)

	def test_attachments_reference_files(self) -> None:
		attachments = build_attachments("abc123")
		self.assertEqual(attachments, [{"fid": "abc123"}])

	def test_ride_format_covers_factura_guia_and_retencion(self) -> None:
		self.assertEqual(ride_print_format("01"), "SRI RIDE")
		self.assertEqual(ride_print_format("06"), "SRI RIDE Delivery Note")
		self.assertEqual(ride_print_format("07"), "SRI RIDE Withholding")

	def test_ride_format_rejects_unknown_code(self) -> None:
		with self.assertRaises(ValueError):
			ride_print_format("99")

	def test_attachments_pair_xml_with_guia_ride(self) -> None:
		self.assertEqual(
			build_attachments("fid-6", "06", "Delivery Note", "DN-1"),
			[
				{"fid": "fid-6"},
				{
					"print_format_attachment": 1,
					"doctype": "Delivery Note",
					"name": "DN-1",
					"print_format": "SRI RIDE Delivery Note",
				},
			],
		)

	def test_attachments_pair_xml_with_retencion_ride(self) -> None:
		self.assertEqual(
			build_attachments("fid-7", "07", "Purchase Invoice", "PINV-1"),
			[
				{"fid": "fid-7"},
				{
					"print_format_attachment": 1,
					"doctype": "Purchase Invoice",
					"name": "PINV-1",
					"print_format": "SRI RIDE Withholding",
				},
			],
		)

	def test_send_guia_mail_to_customer(self) -> None:
		fake = _FakeFrappe(
			{("SRI Electronic Voucher", "V-06"): _voucher("06", "Delivery Note", "DN-1")},
			{
				("Delivery Note", "DN-1", "customer"): "CUST-1",
				("Customer", "CUST-1", "email_id"): "c@example.com",
				("File", (("file_url", "/private/files/v06.xml"),), "name"): "fid-6",
			},
		)
		result = _send_with(fake, "V-06")
		self.assertEqual(result["recipients"], ["c@example.com"])
		self.assertEqual(result["attachments"][0], {"fid": "fid-6"})
		self.assertEqual(result["attachments"][1]["print_format"], "SRI RIDE Delivery Note")

	def test_send_retencion_mail_to_supplier_contact_fallback(self) -> None:
		contact_key = (
			"Contact",
			(
				("is_primary_contact", 1),
				("link_doctype", "Supplier"),
				("link_name", "SUP-1"),
			),
			"email_id",
		)
		fake = _FakeFrappe(
			{("SRI Electronic Voucher", "V-07"): _voucher("07", "Purchase Invoice", "PINV-1")},
			{
				("Purchase Invoice", "PINV-1", "supplier"): "SUP-1",
				("Supplier", "SUP-1", "email_id"): None,
				contact_key: "ap@example.com",
				("File", (("file_url", "/private/files/v07.xml"),), "name"): "fid-7",
			},
		)
		result = _send_with(fake, "V-07")
		self.assertEqual(result["recipients"], ["ap@example.com"])
		self.assertEqual(result["attachments"][1]["print_format"], "SRI RIDE Withholding")

	def test_send_skips_non_authorized_voucher(self) -> None:
		voucher = _voucher("06", "Delivery Note", "DN-1")
		voucher.voucher_state = "Received"
		fake = _FakeFrappe({("SRI Electronic Voucher", "V-06"): voucher}, {})
		self.assertIsNone(_send_with(fake, "V-06"))
		self.assertEqual(fake.sent, [])

	def test_send_rejects_unknown_document_code(self) -> None:
		voucher = _voucher("99", "Delivery Note", "DN-1")
		fake = _FakeFrappe(
			{("SRI Electronic Voucher", "V-99"): voucher},
			{
				("Delivery Note", "DN-1", "customer"): "CUST-1",
				("Customer", "CUST-1", "email_id"): "c@example.com",
				("File", (("file_url", "/private/files/v99.xml"),), "name"): "fid-9",
			},
		)
		with self.assertRaises(ValueError):
			_send_with(fake, "V-99")


def _voucher(cod_doc: str, reference_doctype: str, reference_name: str):
	"""Authorized voucher stand-in for `send` tests."""
	return SimpleNamespace(
		name=_sri_number(cod_doc),
		voucher_state="Authorized",
		sri_doc_code=cod_doc,
		company="Test Company",
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		access_key="1" * 49,
		signed_xml=f"/private/files/v{cod_doc}.xml",
	)


def _send_with(fake: _FakeFrappe, voucher_name: str):
	"""Run `send_authorized_voucher_mail` with a fake `frappe` module."""
	real_frappe = voucher_mail.frappe
	voucher_mail.frappe = fake
	try:
		return voucher_mail.send_authorized_voucher_mail(voucher_name)
	finally:
		voucher_mail.frappe = real_frappe
