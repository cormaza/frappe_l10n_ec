"""SRI Electronic Voucher state machine (pure Python, no frappe).

`Returned` (SRI sent the voucher back for correction) is reworkable via
`regenerate`; `Rejected` (authorization denied) is terminal. `Annulled`
records a SRI-side void (manual portal/presencial tramite, no SRI void API)
and is terminal: only `Authorized` vouchers void, via `void`.
"""

STATES = ("Generated", "Signed", "Received", "Authorized", "Returned", "Rejected", "Annulled")

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


TERMINAL_STATES = ("Authorized", "Rejected", "Annulled")

TRANSITIONS = {
	("Generated", "sign"): "Signed",
	("Signed", "receive_ok"): "Received",
	("Signed", "receive_fail"): "Returned",
	("Received", "authorize_ok"): "Authorized",
	("Received", "authorize_fail"): "Rejected",
	("Returned", "regenerate"): "Generated",
	("Authorized", "void"): "Annulled",
}


class SriVoucherError(ValueError):
	"""Raised for illegal voucher state transitions."""


def next_state(current: str, event: str) -> str:
	"""Return the state following `event`, or raise `SriVoucherError`."""
	try:
		return TRANSITIONS[(current, event)]
	except KeyError:
		raise SriVoucherError(_("Cannot apply event '{}' in state '{}'.").format(event, current)) from None


def is_terminal(state: str) -> bool:
	"""Whether polling must stop (authorized or rejected)."""
	return state in TERMINAL_STATES
