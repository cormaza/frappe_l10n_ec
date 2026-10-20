import unittest

from l10n_ec.ecuador_localization.voucher_mail import (
	authorized_mail_subject,
	build_attachments,
	resolve_recipients,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


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
