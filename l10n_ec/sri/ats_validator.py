"""ATS DIMM-validator integration: staleness contract plus bench calls.

The validator is an independent sidecar (see docker_ats_validator): this
module never reimplements SRI rules. It owns the version contract that lets
the service advertise "estoy desactualizado":

* :data:`EXPECTED_VALIDATOR` pins the SRI stack this app release was tested
  against (plugin zip + libs date, mirrored from the service's
  ``validator.properties``).
* :func:`check_staleness` compares a ``GET /version`` payload against it.
* Bench entry points (:func:`validator_status`, :func:`validate_month`)
  read the endpoint/token from ``site_config.json``
  (``ats_validator_url``, ``ats_validator_token``) and fail loud when the
  service is unreachable or answers outside its contract — never implied
  valid. Pure helpers stay Ring-1 importable via the ``frappe`` guard.
"""

try:
	import frappe
	from frappe import _
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message


#: SRI stack this app release validates against (mirror of validator.properties).
EXPECTED_VALIDATOR = {
	"sriPluginZip": "ats.plugin.1.19.0",
	"sriLibsDate": "2026-09-07",
}

DEFAULT_VALIDATOR_URL = "http://127.0.0.1:8080"
REQUEST_TIMEOUT = 120


def check_staleness(reported: dict) -> tuple:
	"""Compare a ``GET /version`` payload with :data:`EXPECTED_VALIDATOR`.

	Returns ``(stale: bool, reason: str)``. Anything outside the contract
	(missing keys, empty values) reads as stale: an unknown validator is
	never treated as current.
	"""
	reported = reported or {}
	problems = []
	for key in ("sriPluginZip", "sriLibsDate"):
		want = EXPECTED_VALIDATOR[key]
		got = (reported.get(key) or "").strip() if isinstance(reported.get(key), str) else reported.get(key)
		if not got:
			problems.append(_("validator reports no '{}'").format(key))
		elif got != want:
			problems.append(_("validator '{}' is '{}', expected '{}'").format(key, got, want))
	if problems:
		return (True, "; ".join(problems))
	return (False, "")


def _validator_config() -> tuple:
	"""(base_url, token) from site config; fail loud without frappe."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to reach the ATS validator.")
	conf = frappe.get_site_config() or {}
	return (
		(conf.get("ats_validator_url") or DEFAULT_VALIDATOR_URL).rstrip("/"),
		conf.get("ats_validator_token") or "",
	)


@frappe.whitelist() if frappe else (lambda fn: fn)
def validator_status() -> dict:
	"""Query the sidecar ``GET /version`` and report staleness for the UI.

	Returns ``{reachable, stale, reason, reported}``; unreachable is data,
	not an exception, so the report can render "no validado" explicitly.
	"""
	import requests

	url, token = _validator_config()
	headers = {"X-Validator-Token": token} if token else {}
	try:
		response = requests.get(f"{url}/version", headers=headers, timeout=10)
		response.raise_for_status()
		reported = response.json()
	except Exception as exc:
		return {"reachable": False, "stale": True, "reason": str(exc), "reported": {}}
	stale, reason = check_staleness(reported if isinstance(reported, dict) else {})
	return {"reachable": True, "stale": stale, "reason": reason, "reported": reported}


@frappe.whitelist() if frappe else (lambda fn: fn)
def validate_month(company: str, year: int, month: int) -> dict:
	"""Validate one posted month through the sidecar; return the receipt.

	Generates the ATS files locally, POSTs the XML, persists the DIMM
	talón HTML as a private File, and returns ``{verdict, stale, reason,
	versions, messages, talon_url, counts}``. ``verdict`` is ``valid``,
	``observed`` (errors/warnings), or ``unavailable`` — never implied.
	"""
	import requests

	from l10n_ec.ecuador_localization.ats_reader import generate_ats_files

	url, token = _validator_config()
	status = validator_status()
	if not status["reachable"]:
		return {
			"verdict": "unavailable",
			"stale": True,
			"reason": status["reason"],
			"versions": {},
			"messages": [],
			"talon_url": "",
			"counts": {},
		}
	result = generate_ats_files(company, int(year), int(month))
	headers = {"X-Validator-Token": token} if token else {}
	response = requests.post(
		f"{url}/validateXml",
		data={"xml_file": result["xml"]},
		headers=headers,
		timeout=REQUEST_TIMEOUT,
	)
	if response.status_code != 200:
		return {
			"verdict": "unavailable",
			"stale": status["stale"],
			"reason": _("validator answered HTTP {}.").format(response.status_code),
			"versions": status["reported"],
			"messages": [],
			"talon_url": "",
			"counts": result["counts"],
		}
	body = response.json()
	messages = body.get("messages") or []
	talon_url = ""
	talon_html = body.get("talon_resumen") or ""
	if talon_html:
		existing = frappe.db.get_value("File", {"file_name": _talon_name(year, month)}, "name")
		if existing:
			frappe.delete_doc("File", existing, ignore_permissions=True, force=True)
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": _talon_name(year, month),
				"content": talon_html.encode("utf-8"),
				"is_private": 1,
			}
		).insert(ignore_permissions=True)
		talon_url = file_doc.file_url
	verdict = "valid"
	if body.get("has_errors"):
		verdict = "observed"
	elif body.get("has_warning"):
		verdict = "observed"
	return {
		"verdict": verdict,
		"stale": status["stale"],
		"reason": status["reason"],
		"versions": status["reported"],
		"messages": messages,
		"talon_url": talon_url,
		"talon_html": talon_html,
		"counts": result["counts"],
	}


def _talon_name(year: int, month: int) -> str:
	"""Private File name for a month talón."""
	return f"AT{int(month):02d}{int(year)}-talon.html"
