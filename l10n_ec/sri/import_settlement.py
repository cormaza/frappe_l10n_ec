"""SRI import settlement arithmetic (pure Python, no frappe).

T1 scope: CIF composition (FOB + freight + insurance), tribute computation
(AD VALOREM and FODINFA from caller-supplied rates — the DAI/tariff owns
the percentages, this module never hardcodes them), and the IVA base per
LRTI Art. 59 (customs value plus duties from the import declaration).
No DocTypes, no file parsing, no reports.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


import re

from l10n_ec.sri.tax_codes import tax_codes_for_template


def _amount(value: float | None, name: str) -> float:
	"""Coerce a non-negative amount, fail loud otherwise."""
	if value is None:
		raise ValueError(_("Import settlement amount '{}' is required.").format(name))
	amount = float(value)
	if amount < 0:
		raise ValueError(
			_("Import settlement amount '{}' cannot be negative (got '{}').").format(name, amount)
		)
	return amount


def _rate(value: float | None, name: str) -> float:
	"""Coerce a non-negative rate percent, fail loud otherwise.

	Zero is a valid exemption; ``None`` means the DAI/tariff gave no rate
	and must be provided, never assumed.
	"""
	if value is None:
		raise ValueError(_("Import settlement rate '{}' is required (never assumed).").format(name))
	rate = float(value)
	if rate < 0:
		raise ValueError(_("Import settlement rate '{}' cannot be negative (got '{}').").format(name, rate))
	return rate


def compute_cif(fob: float, freight: float, insurance: float) -> float:
	"""Customs value (CIF): FOB + freight + insurance, rounded 2."""
	return round(
		_amount(fob, "fob") + _amount(freight, "freight") + _amount(insurance, "insurance"),
		2,
	)


def compute_ad_valorem(cif: float, rate_pct: float | None) -> float:
	"""AD VALOREM duty: CIF x tariff rate from the DAI, rounded 2."""
	return round(_amount(cif, "cif") * _rate(rate_pct, "ad_valorem") / 100.0, 2)


def compute_fodinfa(cif: float, rate_pct: float | None) -> float:
	"""FODINFA: CIF x rate from the DAI, rounded 2."""
	return round(_amount(cif, "cif") * _rate(rate_pct, "fodinfa") / 100.0, 2)


def compute_iva_base(
	cif: float,
	ad_valorem: float = 0.0,
	fodinfa: float = 0.0,
	ice: float = 0.0,
	other_duties: float = 0.0,
) -> float:
	"""IVA base per LRTI Art. 59: customs value plus duties, rounded 2."""
	return round(
		_amount(cif, "cif")
		+ _amount(ad_valorem, "ad_valorem")
		+ _amount(fodinfa, "fodinfa")
		+ _amount(ice, "ice")
		+ _amount(other_duties, "other_duties"),
		2,
	)


def compute_iva(iva_base: float, rate_pct: float | None) -> float:
	"""IVA on the Art. 59 base at the caller-supplied rate, rounded 2."""
	return round(_amount(iva_base, "iva_base") * _rate(rate_pct, "iva") / 100.0, 2)


def compute_import_taxes(
	fob: float,
	freight: float,
	insurance: float,
	ad_valorem_rate_pct: float | None,
	fodinfa_rate_pct: float | None,
	iva_rate_pct: float | None,
	ice: float = 0.0,
	other_duties: float = 0.0,
) -> dict:
	"""Full settlement chain returning every intermediate value.

	Rates travel in from the DAI/tariff; amounts accumulate from the linked
	source documents (PO freight/insurance lines, forwarder invoices).
	"""
	cif = compute_cif(fob, freight, insurance)
	ad_valorem = compute_ad_valorem(cif, ad_valorem_rate_pct)
	fodinfa = compute_fodinfa(cif, fodinfa_rate_pct)
	iva_base = compute_iva_base(cif, ad_valorem, fodinfa, ice, other_duties)
	return {
		"cif": cif,
		"ad_valorem": ad_valorem,
		"fodinfa": fodinfa,
		"ice": round(_amount(ice, "ice"), 2),
		"other_duties": round(_amount(other_duties, "other_duties"), 2),
		"iva_base": iva_base,
		"iva": compute_iva(iva_base, iva_rate_pct),
	}


def is_foreign_country(country_name: str | None) -> bool:
	"""Whether a country name proves a non-Ecuadorian party.

	Tri-state by name, mirroring the country-evidence doctrine: an empty
	or missing country is unknown and never restricts; only an explicit
	non-Ecuadorian name counts as foreign.
	"""
	if country_name is None:
		return False
	name = country_name.strip()
	if not name:
		return False
	return name.lower() != "ecuador"


def validate_no_local_vat(country_name: str | None, templates: list | tuple | None) -> None:
	"""Fail loud when an exterior purchase carries Ecuadorian VAT templates.

	A foreign supplier never charges local VAT: the import VAT credit is
	born by the DAI liquidation (settlement-computed Art. 59 base), never
	by the supplier invoice. Any VAT-impuesto template (any rate, even
	zero) on a proven-foreign purchase is a data error; unknown country
	never restricts.
	"""
	if not is_foreign_country(country_name):
		return
	offenders = []
	for template in dict.fromkeys(templates or []):
		if not template:
			continue
		code, _rate_code = tax_codes_for_template(template)
		if code == "2":
			offenders.append(template)
	if offenders:
		raise ValueError(
			_(
				"Exterior purchases carry no local VAT (template '{}' is Ecuadorian VAT); "
				"the import VAT credit comes from the DAI settlement, not the supplier invoice."
			).format("', '".join(offenders))
		)


def validate_partida(code: str | None) -> str:
	"""Validate a national subpartida: exactly 10 digits (NANDINA 8+2).

	No rate lookup here: percentages always travel in with the DAI, the
	catalog only keys the company's reusable knowledge.
	"""
	cleaned = (code or "").strip()
	if not re.fullmatch(r"\d{10}", cleaned):
		raise ValueError(_("Import partida '{}' must be a 10-digit national subpartida.").format(code))
	return cleaned
