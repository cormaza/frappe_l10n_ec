"""Unit tests for the SRI void (anulacion) lifecycle (pure Python, mocked frappe)."""

import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from l10n_ec.sri.ats_collector import collect_cancelled
from l10n_ec.sri.voucher_states import SriVoucherError, is_terminal, next_state

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

VOIDABLE_STATES = ("Generated", "Signed", "Received", "Returned", "Rejected", "Annulled")


class TestVoidTransition(UnitTestCase):
	"""The transition table owns void: Authorized voids, all else fails loud."""

	def test_authorized_voids_to_annulled(self) -> None:
		self.assertEqual(next_state("Authorized", "void"), "Annulled")
		self.assertTrue(is_terminal("Annulled"))

	def test_void_rejected_from_every_other_state(self) -> None:
		for current in VOIDABLE_STATES:
			with self.assertRaises(SriVoucherError):
				next_state(current, "void")


def _fake_voucher(state="Authorized", **overrides):
	"""In-memory voucher doc with a recordable save (no frappe)."""
	doc = SimpleNamespace(
		voucher_state=state,
		sri_doc_code="01",
		sri_number="001-001-000000001",
		authorization_number="AUTH001",
		authorization_date="20/10/2026 10:30:00",
		last_message="",
		saved=False,
		void_date=None,
		void_reason="",
	)
	for key, value in overrides.items():
		setattr(doc, key, value)

	def save(ignore_permissions=False):
		doc.saved = True

	doc.save = save
	return doc


class TestRequestVoid(UnitTestCase):
	"""`request_void` records the manual SRI-side void on Authorized vouchers."""

	def _run(self, doc, **kwargs):
		from l10n_ec.ecuador_localization import voucher_flow

		fake_frappe = SimpleNamespace(get_doc=lambda doctype, name: doc)
		with patch.object(voucher_flow, "frappe", fake_frappe):
			return voucher_flow.request_void("VOID-1", **kwargs)

	def test_success_stamps_metadata_and_saves(self) -> None:
		doc = _fake_voucher()
		state = self._run(doc, reason="Duplicate emission")
		self.assertEqual(state, "Annulled")
		self.assertEqual(doc.voucher_state, "Annulled")
		self.assertEqual(doc.void_date, date.today())
		self.assertEqual(doc.void_reason, "Duplicate emission")
		self.assertTrue(doc.saved)
		self.assertIn("Void recorded", doc.last_message)

	def test_explicit_void_date_is_kept(self) -> None:
		doc = _fake_voucher()
		self._run(doc, void_date="2026-10-20", reason="Carta SRI 123")
		self.assertEqual(doc.void_date, "2026-10-20")
		self.assertIn("2026-10-20", doc.last_message)

	def test_missing_reason_defaults_to_empty(self) -> None:
		doc = _fake_voucher()
		self._run(doc)
		self.assertEqual(doc.void_reason, "")

	def test_non_authorized_states_refuse_without_saving(self) -> None:
		for state in VOIDABLE_STATES:
			doc = _fake_voucher(state=state)
			with self.assertRaises(SriVoucherError):
				self._run(doc, reason="nope")
			self.assertEqual(doc.voucher_state, state)
			self.assertFalse(doc.saved)

	def test_needs_frappe(self) -> None:
		from l10n_ec.ecuador_localization import voucher_flow

		with patch.object(voucher_flow, "frappe", None):
			with self.assertRaises(RuntimeError):
				voucher_flow.request_void("VOID-1")


class FakeFrappe:
	"""Minimal frappe surface for `read_month`: vouchers keyed by state."""

	def __init__(self, vouchers):
		self.vouchers = vouchers
		self.db = SimpleNamespace(
			get_value=lambda doctype, name, field=None, **kwargs: (
				{"tax_id": "1760013210001", "company_name": "Demo Ecuador"}
				if doctype == "Company"
				else None
			)
		)

	def get_all(self, doctype, filters=None, pluck=None):
		if doctype == "SRI Electronic Voucher":
			wanted = (filters or {}).get("voucher_state")
			return [name for name, doc in self.vouchers.items() if doc["voucher_state"] == wanted]
		return []

	def get_doc(self, doctype, name):
		return dict(self.vouchers[name])


class TestAtsAnnulledSourcing(UnitTestCase):
	"""`read_month` sources Annulled vouchers into cancelled with SRI numbers."""

	ANNULLED = {
		"sri_doc_code": "01",
		"sri_number": "001-001-000000001",
		"authorization_number": "AUTH001",
		"voucher_state": "Annulled",
	}

	def test_annulled_row_feeds_cancelled_with_auth(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import annulled_row

		row = collect_cancelled(annulled_row(dict(self.ANNULLED)))
		self.assertEqual(row["tipoComprobante"], "01")
		self.assertEqual(row["secuencialInicio"], "000000001")
		self.assertEqual(row["secuencialFin"], "000000001")
		self.assertEqual(row["autorizacion"], "AUTH001")

	def test_read_month_sources_only_annulled_vouchers(self) -> None:
		from l10n_ec.ecuador_localization import ats_reader

		vouchers = {
			"VOID-1": dict(self.ANNULLED),
			"VOID-2": {
				"sri_doc_code": "04",
				"sri_number": "001-001-000000002",
				"authorization_number": "AUTH002",
				"voucher_state": "Annulled",
			},
			"REJ-1": {
				"sri_doc_code": "01",
				"sri_number": "001-001-000000003",
				"authorization_number": "",
				"voucher_state": "Rejected",
			},
		}
		with patch.object(ats_reader, "frappe", FakeFrappe(vouchers)):
			month = ats_reader.read_month("Demo Ecuador", 2026, 10)
		cancelled = month["cancelled"]
		self.assertEqual(len(cancelled), 2)
		by_number = {row["sri_number"]: row for row in cancelled}
		self.assertEqual(by_number["001-001-000000001"]["auth_number"], "AUTH001")
		self.assertEqual(by_number["001-001-000000002"]["doc_code"], "04")
		self.assertNotIn("001-001-000000003", by_number)

	def test_read_month_without_annulled_vouchers_stays_empty(self) -> None:
		from l10n_ec.ecuador_localization import ats_reader

		with patch.object(ats_reader, "frappe", FakeFrappe({})):
			month = ats_reader.read_month("Demo Ecuador", 2026, 10)
		self.assertEqual(month["cancelled"], [])


if __name__ == "__main__":
	unittest.main()
