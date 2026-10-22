"""Unit tests for the ATS validator version contract (pure, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.ats_validator import EXPECTED_VALIDATOR, check_staleness


class TestValidatorStaleness(UnitTestCase):
	def test_current_validator_is_not_stale(self) -> None:
		reported = dict(EXPECTED_VALIDATOR)
		reported["service"] = "1.3.0"
		stale, reason = check_staleness(reported)
		self.assertFalse(stale)
		self.assertEqual(reason, "")

	def test_old_plugin_zip_is_stale(self) -> None:
		stale, reason = check_staleness(
			{"sriPluginZip": "ats.plugin.1.18.0", "sriLibsDate": EXPECTED_VALIDATOR["sriLibsDate"]}
		)
		self.assertTrue(stale)
		self.assertIn("ats.plugin.1.18.0", reason)

	def test_old_libs_date_is_stale(self) -> None:
		stale, reason = check_staleness(
			{"sriPluginZip": EXPECTED_VALIDATOR["sriPluginZip"], "sriLibsDate": "2025-01-27"}
		)
		self.assertTrue(stale)
		self.assertIn("2025-01-27", reason)

	def test_missing_keys_read_as_stale_never_current(self) -> None:
		for reported in ({}, {"sriPluginZip": ""}, {"sriLibsDate": None}):
			stale, _reason = check_staleness(reported)
			self.assertTrue(stale)
