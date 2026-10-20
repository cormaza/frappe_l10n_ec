import unittest

from l10n_ec.ecuador_localization.invoice_hooks import validate_sri_invoice

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class _StubInvoice:
	def __init__(self, **values):
		self._values = values

	def get(self, key, default=None):
		return self._values.get(key, default)


class TestInvoiceHooks(UnitTestCase):
	"""Unit tests for the SRI invoice hooks (no database; frappe absent)."""

	def test_missing_customer_skips_validation(self) -> None:
		self.assertIsNone(validate_sri_invoice(_StubInvoice(grand_total=1000.0)))

	def test_unknown_customer_skips_validation(self) -> None:
		doc = _StubInvoice(customer="Nonexistent Customer", grand_total=1000.0)
		self.assertIsNone(validate_sri_invoice(doc))
