"""Ecuadorian taxpayer identification validation (SRI types 04-08).

RUC and Cédula checksum logic is delegated to `python-stdnum`
(`stdnum.ec.ruc`, `stdnum.ec.ci`), mirroring `odoo/addons/l10n_ec`.
Pasaporte (06) and Exterior (08) have no checksum standard, so only
presence is checked. Consumidor Final (07) is the fixed literal below;
its amount threshold is a billing rule, not validated here.
"""

from stdnum.ec import ci, ruc

FINAL_CONSUMER_ID = "9999999999999"

_CHECKED_VALIDATORS = {
	"04": ruc.is_valid,
	"05": ci.is_valid,
}


def validate_ruc(value: str) -> bool:
	"""Validate a 13-digit Ecuadorian RUC (`04`)."""
	return ruc.is_valid((value or "").strip())


def validate_ci(value: str) -> bool:
	"""Validate a 10-digit Ecuadorian Cédula (`05`)."""
	return ci.is_valid((value or "").strip())


def validate_identification(type_code: str, value: str) -> bool:
	"""Dispatch validation by SRI identification type code (`04`-`08`)."""
	cleaned_value = (value or "").strip()
	code = (type_code or "").strip()
	if code in _CHECKED_VALIDATORS:
		return _CHECKED_VALIDATORS[code](cleaned_value)
	if code in ("06", "08"):
		return bool(cleaned_value)
	if code == "07":
		return cleaned_value == FINAL_CONSUMER_ID
	return False


def validate_identification_with_fallback(type_code: str, value: str, fetch=None) -> tuple:
	"""Validate with the SRI registry as soft fallback (pure, no frappe).

	Returns ``(ok, path)`` where path is ``stdnum`` (checksum passed, the
	network is never touched), ``sri`` (checksum failed but the registry
	knows the number), ``rejected`` (registry answers unknown) or
	``unverifiable`` (registry unreachable or unusable). Only RUC (`04`)
	queries the registry: every other type keeps its current verdict.
	"""
	from l10n_ec.sri.ruc_lookup import lookup_ruc

	cleaned_value = (value or "").strip()
	code = (type_code or "").strip()
	if validate_identification(code, cleaned_value):
		return (True, "stdnum")
	if code != "04" or not cleaned_value:
		return (False, "rejected")
	verdict = lookup_ruc(cleaned_value, fetch=fetch)
	if verdict["known"] is True:
		return (True, "sri")
	if verdict["known"] is False:
		return (False, "rejected")
	return (False, "unverifiable")
