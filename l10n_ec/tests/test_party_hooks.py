import unittest
from unittest.mock import patch

from l10n_ec.ecuador_localization import party_hooks

try:
	import frappe
	from frappe.tests import UnitTestCase

	EXPECTED_ERROR = (ValueError, frappe.ValidationError)
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]
	EXPECTED_ERROR = ValueError


class _StubDoc:
	"""Minimal Document stand-in exposing `.get`, `doctype`, and `name`."""

	def __init__(self, doctype="Customer", name="TEST-001", **values):
		self.doctype = doctype
		self.name = name
		self._values = values

	def get(self, key, default=None):
		return self._values.get(key, default)


class TestPartyHooks(UnitTestCase):
	"""Unit tests for the Customer/Supplier SRI validation hook (no database)."""

	def test_missing_identification_type_skips_validation(self) -> None:
		doc = _StubDoc(tax_id="not-a-ruc")
		self.assertIsNone(party_hooks.validate_sri_identification(doc))

	def test_unresolvable_country_skips_validation(self) -> None:
		doc = _StubDoc(sri_identification_type="04", tax_id="not-a-ruc")
		self.assertIsNone(party_hooks.validate_sri_identification(doc))

	def test_invalid_ecuadorian_tax_id_raises(self) -> None:
		doc = _StubDoc(sri_identification_type="04", tax_id="1790016819001")
		with patch.object(party_hooks, "_resolve_country_code", return_value="EC"):
			with self.assertRaises(EXPECTED_ERROR):
				party_hooks.validate_sri_identification(doc)

	def test_valid_ecuadorian_tax_id_passes(self) -> None:
		doc = _StubDoc(sri_identification_type="04", tax_id="1790016919001")
		with patch.object(party_hooks, "_resolve_country_code", return_value="EC"):
			self.assertIsNone(party_hooks.validate_sri_identification(doc))
