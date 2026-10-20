"""SRI Electronic Voucher state machine (pure Python, no frappe).

`Returned` (SRI sent the voucher back for correction) is reworkable via
`regenerate`; `Rejected` (authorization denied) is terminal.
"""

STATES = ("Generated", "Signed", "Received", "Authorized", "Returned", "Rejected")

TERMINAL_STATES = ("Authorized", "Rejected")

TRANSITIONS = {
	("Generated", "sign"): "Signed",
	("Signed", "receive_ok"): "Received",
	("Signed", "receive_fail"): "Returned",
	("Received", "authorize_ok"): "Authorized",
	("Received", "authorize_fail"): "Rejected",
	("Returned", "regenerate"): "Generated",
}


class SriVoucherError(ValueError):
	"""Raised for illegal voucher state transitions."""


def next_state(current: str, event: str) -> str:
	"""Return the state following `event`, or raise `SriVoucherError`."""
	try:
		return TRANSITIONS[(current, event)]
	except KeyError:
		raise SriVoucherError(f"Cannot apply event '{event}' in state '{current}'.") from None


def is_terminal(state: str) -> bool:
	"""Whether polling must stop (authorized or rejected)."""
	return state in TERMINAL_STATES
