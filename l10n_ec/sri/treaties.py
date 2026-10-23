"""Exterior withholding rates: treaties and domestic regimes (pure, sourced).

Every rate below quotes its primary source; unknown pairs fail loud instead
of guessing. Country keys are ISO codes (``Country.code``, same as
``company_country_code``).

Domestic regimes (Ecuadorian law, no treaty needed):
- ``SIN_CONVENIO_RATE`` (25.0): tarifa general de sociedades, LRTI Art. 37
  (R.O. 587, 29-XI-2021); applied by NAC-DGERCGC26-00000009 Art. 4 to
  occasional services and other unrated payments abroad.
- ``PARAISO_RATE`` (37.0): máxima tarifa de personas naturales 2026,
  NAC-DGERCGC25-00000043; applied by LRTI Art. 39 to income perceived in
  paraísos fiscales / low-tax jurisdictions / preferential regimes.

Treaties (rate caps on Ecuadorian source withholding; residence must be
proven per NAC-DGERCGC24-00000008 Art. 9):
- ES (España, CDI BOE): 501A regalías 10% (art. 12.2; 5% only for
  copyright, not demoed), 504 dividendos 15% (art. 10.2, beneficiario
  efectivo).

Country-to-regime mapping is deliberately absent: the SRI paraíso list is
versioned elsewhere, and guessing paraíso/sin-convenio silently would
misstate tax. Callers pass the regime explicitly; ``treaty_rate`` only
resolves con-convenio pairs.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


#: Tarifa general de sociedades (LRTI Art. 37).
SIN_CONVENIO_RATE = 25.0
#: Máxima tarifa de personas naturales 2026 (NAC-DGERCGC25-00000043).
PARAISO_RATE = 37.0

#: {(country_iso, concepto): (rate, source)} — CDI caps, con-convenio only.
TREATY_RATES = {
	("ES", "501A"): (10.0, "CDI Ecuador-España BOE art. 12.2 (cánones, 10%)"),
	("ES", "504"): (15.0, "CDI Ecuador-España BOE art. 10.2 (dividendos, beneficiario efectivo)"),
}


def treaty_rate(country_iso: str | None, concepto: str) -> tuple:
	"""Return ``(rate, source)`` for a treaty pair; fail loud when unknown."""
	key = ((country_iso or "").strip().upper(), (concepto or "").strip().upper())
	if key not in TREATY_RATES:
		raise ValueError(
			_("No sourced treaty rate for '{}' in '{}'; add it with its CDI article.").format(
				concepto, country_iso
			)
		)
	return TREATY_RATES[key]
