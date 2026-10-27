"""Unit tests for SRI import settlement links (T2: pure link-set validation)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.import_links import GOODS_ROLES, LINK_DOCTYPES, validate_settlement_links


def _links(**kwargs):
	base = {"purchase_order": None, "purchase_receipt": None, "purchase_invoice": None}
	base.update(kwargs)
	return {
		role: ((LINK_DOCTYPES[role], name) if name else None) for role, name in base.items()
	}


class TestSettlementLinkSet(UnitTestCase):
	def test_goods_invoice_alone_passes(self) -> None:
		validate_settlement_links("Demo Ecuador", _links(purchase_invoice="ACC-PINV-2026-00001"))

	def test_goods_order_alone_passes(self) -> None:
		validate_settlement_links("Demo Ecuador", _links(purchase_order="PO-2026-00001"))

	def test_cost_invoices_ride_along_goods_source(self) -> None:
		validate_settlement_links(
			"Demo Ecuador",
			{
				**_links(purchase_invoice="ACC-PINV-2026-00001"),
				"freight_invoice": ("Purchase Invoice", "ACC-PINV-2026-00002"),
				"insurance_invoice": ("Purchase Invoice", "ACC-PINV-2026-00003"),
			},
		)

	def test_missing_company_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_settlement_links(None, _links(purchase_invoice="ACC-PINV-2026-00001"))

	def test_no_goods_source_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_settlement_links(
				"Demo Ecuador",
				{
					**_links(),
					"freight_invoice": ("Purchase Invoice", "ACC-PINV-2026-00002"),
				},
			)

	def test_same_document_in_two_roles_fails(self) -> None:
		with self.assertRaises(ValueError):
			validate_settlement_links(
				"Demo Ecuador",
				{
					**_links(purchase_invoice="ACC-PINV-2026-00001"),
					"freight_invoice": ("Purchase Invoice", "ACC-PINV-2026-00001"),
				},
			)

	def test_goods_roles_cover_po_pr_pi(self) -> None:
		self.assertEqual(GOODS_ROLES, ("purchase_order", "purchase_receipt", "purchase_invoice"))
