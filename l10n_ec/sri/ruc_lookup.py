"""SRI RUC soft-check via the public móvil endpoint (no auth, fail-open verdicts).

The SRI issues RUCs without check-digit validation (2021 comunicado for
private/public societies and foreign individuals; python-stdnum #497 for
third-digit-9 societies), so a stdnum rejection never proves a fake RUC.
This module asks the SRI registry itself and returns a verdict — it never
raises on transport failures and never blocks a save by itself.

Pure Python, no frappe, no third-party HTTP client (stdlib ``urllib``):
Ring 1 tests inject ``fetch``; bench uses the default with a short timeout.
"""

import json
import urllib.request

#: Public SRI móvil registry endpoint (reverse-engineered from app v1.37.0;
#: may change or rate-limit without notice — hence verdicts, not reliance).
ESTADO_TRIBUTARIO_URL = "https://srienlinea.sri.gob.ec/movil-servicios/api/v1.0/estadoTributario"

#: Seconds before the soft-check gives up (a save must never hang on SRI).
LOOKUP_TIMEOUT = 4.0


def _default_fetch(ruc: str, timeout: float = LOOKUP_TIMEOUT) -> dict:
	"""GET estadoTributario; returns ``{status, payload}`` or raises."""
	request = urllib.request.Request(
		f"{ESTADO_TRIBUTARIO_URL}/{ruc.strip()}",
		headers={"Accept": "application/json", "User-Agent": "l10n_ec/16.0"},
	)
	with urllib.request.urlopen(request, timeout=timeout) as response:
		body = response.read().decode("utf-8", errors="replace")
		try:
			payload = json.loads(body) if body.strip() else {}
		except ValueError:
			payload = {}
		return {"status": response.status, "payload": payload if isinstance(payload, dict) else {}}


def lookup_ruc(ruc: str, fetch=None, timeout: float = LOOKUP_TIMEOUT) -> dict:
	"""Ask the SRI registry about a RUC; never raises.

	Returns ``{"known": True|False|None, "data": dict, "error": str}``:
	``True`` when the registry answers with taxpayer data, ``False`` when
	it answers unknown (HTTP 404 or empty body), ``None`` when the answer
	itself is unusable (timeout, network, WAF HTML, unparsable body).
	"""
	fetch = fetch or _default_fetch
	try:
		response = fetch((ruc or "").strip(), timeout)
	except Exception as exc:
		return {"known": None, "data": {}, "error": f"sri-unreachable: {exc}"}
	status = response.get("status")
	payload = response.get("payload") or {}
	if status == 404 or not payload:
		return {"known": False, "data": {}, "error": ""}
	if not isinstance(payload, dict) or "razonSocial" not in payload:
		return {"known": None, "data": {}, "error": f"sri-unexpected-body: HTTP {status}"}
	return {"known": True, "data": payload, "error": ""}
