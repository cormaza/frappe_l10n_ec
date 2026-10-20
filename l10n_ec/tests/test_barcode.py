import base64
import unittest

from l10n_ec.ecuador_localization.jinja import sri_authorized_voucher, sri_barcode, sri_emisor
from l10n_ec.sri.barcode import access_key_barcode_data_uri, access_key_barcode_png

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

ACCESS_KEY = "2410202601179001691900110010010000000011234567815"


class TestAccessKeyBarcode(UnitTestCase):
	"""Unit tests for SRI access-key barcode rendering (pure Python)."""

	def test_png_bytes_have_png_magic(self) -> None:
		png = access_key_barcode_png(ACCESS_KEY)
		self.assertTrue(png.startswith(b"\x89PNG"))
		self.assertGreater(len(png), 100)

	def test_rendering_is_deterministic(self) -> None:
		self.assertEqual(access_key_barcode_png(ACCESS_KEY), access_key_barcode_png(ACCESS_KEY))

	def test_data_uri_embeds_png(self) -> None:
		uri = access_key_barcode_data_uri(ACCESS_KEY)
		self.assertTrue(uri.startswith("data:image/png;base64,"))
		raw = base64.b64decode(uri.split(",", 1)[1])
		self.assertTrue(raw.startswith(b"\x89PNG"))

	def test_rejects_non_49_digit_input(self) -> None:
		with self.assertRaises(ValueError):
			access_key_barcode_png("12345")
		with self.assertRaises(ValueError):
			access_key_barcode_png("A" * 49)

	def test_jinja_helpers(self) -> None:
		uri = sri_barcode(ACCESS_KEY)
		self.assertTrue(uri.startswith("data:image/png;base64,"))

	def test_jinja_lookups_return_none_when_absent(self) -> None:
		self.assertIsNone(sri_authorized_voucher("Sales Invoice", "definitely-missing-doc"))
		self.assertIsNone(sri_emisor("Nonexistent Company 123"))
