"""SRI code selectors: code-with-legend values normalize to the bare code.

Selectors show ``"02 - Sin crédito tributario"`` so operators see the legend,
but every fiscal reader needs the bare ``"02"``. `sri_code` splits on the
first ``" - "`` and is idempotent over already-bare codes. Pure Python.
"""


def sri_code(value: str | None) -> str:
	"""Return the bare SRI code from a selector value (legend or bare)."""
	text = (value or "").strip()
	if not text:
		return ""
	return text.split(" - ", 1)[0].strip()
