"""Unit tests for the RUC validation chain (pure, network stubbed)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.identification import validate_identification_with_fallback
from l10n_ec.sri.ruc_lookup import lookup_ruc


def _known_ruc(ruc: str, timeout: float = 4.0):
	return {"status": 200, "payload": {"razonSocial": "EMPRESA EJEMPLO SA", "estadoRuc": "ACTIVO"}}


def _unknown_ruc(ruc: str, timeout: float = 4.0):
	return {"status": 404, "payload": {}}


def _broken_sri(ruc: str, timeout: float = 4.0):
	raise TimeoutError("timed out")


class TestRucLookup(unittest.TestCase):
	def test_known_ruc(self) -> None:
		verdict = lookup_ruc("1790016919001", fetch=_known_ruc)
		self.assertEqual(verdict["known"], True)

	def test_unknown_ruc(self) -> None:
		verdict = lookup_ruc("1790016919001", fetch=_unknown_ruc)
		self.assertEqual(verdict["known"], False)

	def test_broken_sri_is_unverifiable_never_valid(self) -> None:
		verdict = lookup_ruc("1790016919001", fetch=_broken_sri)
		self.assertIsNone(verdict["known"])
		self.assertTrue(verdict["error"])


class TestIdentificationFallback(UnitTestCase):
	def test_stdnum_pass_never_touches_network(self) -> None:
		def _boom(ruc: str, timeout: float = 4.0):
			raise AssertionError("network must not be reached")

		ok, path = validate_identification_with_fallback("04", "1790016919001", fetch=_boom)
		self.assertTrue(ok)
		self.assertEqual(path, "stdnum")

	def test_stdnum_fail_sri_known_soft_pass(self) -> None:
		ok, path = validate_identification_with_fallback("04", "1790000000001", fetch=_known_ruc)
		self.assertTrue(ok)
		self.assertEqual(path, "sri")

	def test_stdnum_fail_sri_unknown_rejects(self) -> None:
		ok, path = validate_identification_with_fallback("04", "1790000000001", fetch=_unknown_ruc)
		self.assertFalse(ok)
		self.assertEqual(path, "rejected")

	def test_stdnum_fail_sri_broken_rejects_with_cause(self) -> None:
		ok, path = validate_identification_with_fallback("04", "1790000000001", fetch=_broken_sri)
		self.assertFalse(ok)
		self.assertEqual(path, "unverifiable")


class FakeCache(dict):
	def get(self, key, default=None):
		return super().get(key, default)

	def set(self, key, value, expires_in_days=None):
		self[key] = value


class TestContactFallbackCache(UnitTestCase):
	def test_sri_path_is_cached(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_contact_tax_id_with_fallback

		calls = []

		def _fetch(ruc: str, timeout: float = 4.0):
			calls.append(ruc)
			return {"status": 200, "payload": {"razonSocial": "X", "estadoRuc": "ACTIVO"}}

		cache = FakeCache()
		self.assertEqual(
			validate_contact_tax_id_with_fallback("EC", "04", "1790000000001", fetch=_fetch, cache=cache),
			"sri",
		)
		self.assertEqual(
			validate_contact_tax_id_with_fallback("EC", "04", "1790000000001", fetch=_fetch, cache=cache),
			"sri",
		)
		self.assertEqual(len(calls), 1)

	def test_stdnum_path_never_caches_nor_fetches(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_contact_tax_id_with_fallback

		def _boom(ruc: str, timeout: float = 4.0):
			raise AssertionError("network must not be reached")

		cache = FakeCache()
		self.assertEqual(
			validate_contact_tax_id_with_fallback("EC", "04", "1790016919001", fetch=_boom, cache=cache),
			"stdnum",
		)
		self.assertEqual(cache, {})

	def test_non_ec_skips(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_contact_tax_id_with_fallback

		self.assertEqual(validate_contact_tax_id_with_fallback("CO", "04", "xxx"), "skipped")


class TestFallbackMessages(UnitTestCase):
	def test_unverifiable_mentions_override(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_contact_tax_id_with_fallback

		def _broken(ruc: str, timeout: float = 4.0):
			raise TimeoutError("timed out")

		with self.assertRaises(ValueError) as ctx:
			validate_contact_tax_id_with_fallback("EC", "04", "1700000000001", fetch=_broken)
		self.assertIn("Skip SRI ID Validation", str(ctx.exception))

	def test_unknown_keeps_classic_message(self) -> None:
		from l10n_ec.ecuador_localization.validation import validate_contact_tax_id_with_fallback

		def _unknown(ruc: str, timeout: float = 4.0):
			return {"status": 404, "payload": {}}

		with self.assertRaises(ValueError) as ctx:
			validate_contact_tax_id_with_fallback("EC", "04", "1700000000001", fetch=_unknown)
		self.assertIn("Invalid tax identification", str(ctx.exception))
