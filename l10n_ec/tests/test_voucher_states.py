import unittest

from l10n_ec.sri.voucher_states import (
	STATES,
	TERMINAL_STATES,
	SriVoucherError,
	is_terminal,
	next_state,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestVoucherStates(UnitTestCase):
	"""Unit tests for the SRI voucher state machine (pure Python)."""

	def test_happy_path_to_authorized(self) -> None:
		state = "Generated"
		for event, expected in (
			("sign", "Signed"),
			("receive_ok", "Received"),
			("authorize_ok", "Authorized"),
		):
			state = next_state(state, event)
			self.assertEqual(state, expected)
		self.assertTrue(is_terminal(state))

	def test_reception_failure_returns_for_rework(self) -> None:
		self.assertEqual(next_state(next_state("Generated", "sign"), "receive_fail"), "Returned")
		self.assertFalse(is_terminal("Returned"))
		self.assertEqual(next_state("Returned", "regenerate"), "Generated")

	def test_authorization_denial_rejects(self) -> None:
		state = next_state(next_state(next_state("Generated", "sign"), "receive_ok"), "authorize_fail")
		self.assertEqual(state, "Rejected")
		self.assertTrue(is_terminal(state))

	def test_illegal_transitions_raise(self) -> None:
		for current, event in (
			("Generated", "receive_ok"),
			("Signed", "authorize_ok"),
			("Authorized", "sign"),
		):
			with self.assertRaises(SriVoucherError):
				next_state(current, event)

	def test_state_inventory(self) -> None:
		self.assertEqual(
			set(STATES), {"Generated", "Signed", "Received", "Authorized", "Returned", "Rejected"}
		)
		self.assertEqual(set(TERMINAL_STATES), {"Authorized", "Rejected"})
