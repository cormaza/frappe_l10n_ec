"""Unit tests for e-commerce shop hooks (pure parts, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.shop_hooks import SHOP_CART_ORDER_TYPE, ensure_shop_point


class TestShopPointGuard(UnitTestCase):
	def test_cart_marker(self) -> None:
		self.assertEqual(SHOP_CART_ORDER_TYPE, "Shopping Cart")

	def test_matching_or_empty_point_passes(self) -> None:
		ensure_shop_point(None, "001-004", "QT-1")
		ensure_shop_point("001-004", "001-004", "QT-1")

	def test_drift_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			ensure_shop_point("001-001", "001-004", "QT-1")
