"""SRI import declaration capture (pure Python, no frappe).

T3 scope: one validated core with two front-ends. The primary front-end
imports a canonical CSV row transcribed from the ECUAPASS liquidation;
the manual fallback types the same fields into the settlement form.
Both produce a ``declaration`` dict that :func:`crosscheck_settlement`
recomputes from costs + rates (T1) and compares against, fail loud.
Real ECUAPASS export mapping stays out until its schema is vendored.
"""

import csv
import io

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.import_settlement import compute_import_taxes

#: Canonical CSV columns: DAI identity, rates owned by the DAI/tariff,
#: then DAI-declared amounts to crosscheck against recomputation.
CSV_COLUMNS = (
	"dai_number",
	"dai_date",
	"ad_valorem_rate",
	"fodinfa_rate",
	"iva_rate",
	"ice",
	"other_duties",
	"dai_ad_valorem",
	"dai_fodinfa",
	"dai_iva",
	"dai_total",
)

#: DAI line-rounding can drift cents against whole-declaration recompute;
#: anything above one dollar is a wrong rate or a wrong CIF, never noise.
CROSSCHECK_TOLERANCE = 1.00


def _number(raw: str | float | None, name: str) -> float:
	if raw is None or (isinstance(raw, str) and not raw.strip()):
		raise ValueError(_("Declaration field '{}' is required.").format(name))
	try:
		return float(raw)
	except (TypeError, ValueError):
		raise ValueError(_("Declaration field '{}' must be numeric (got '{}').").format(name, raw))


def parse_declaration_csv(text: str) -> dict:
	"""Parse one canonical CSV row into rates + declared amounts.

	Fail loud on wrong header, missing/extra rows, or non-numeric cells:
	one file carries exactly one DAI.
	"""
	rows = list(csv.DictReader(io.StringIO(text or "")))
	if not rows:
		raise ValueError(_("Declaration file is empty."))
	if len(rows) > 1:
		raise ValueError(_("Declaration file must carry exactly one DAI (got {}).").format(len(rows)))
	row = rows[0]
	missing = [column for column in CSV_COLUMNS if column not in row]
	if missing:
		raise ValueError(_("Declaration file misses columns: {}.").format(", ".join(missing)))
	rates = {
		"ad_valorem": _number(row["ad_valorem_rate"], "ad_valorem_rate"),
		"fodinfa": _number(row["fodinfa_rate"], "fodinfa_rate"),
		"iva": _number(row["iva_rate"], "iva_rate"),
	}
	declared = {
		"dai_ad_valorem": _number(row["dai_ad_valorem"], "dai_ad_valorem"),
		"dai_fodinfa": _number(row["dai_fodinfa"], "dai_fodinfa"),
		"dai_iva": _number(row["dai_iva"], "dai_iva"),
		"dai_total": _number(row["dai_total"], "dai_total"),
	}
	return {
		"dai_number": (row["dai_number"] or "").strip(),
		"dai_date": (row["dai_date"] or "").strip(),
		"rates": rates,
		"duties": {
			"ice": _number(row["ice"], "ice"),
			"other_duties": _number(row["other_duties"], "other_duties"),
		},
		"declared": declared,
	}


def crosscheck_settlement(
	costs: dict,
	rates: dict,
	declared: dict,
	tolerance: float = CROSSCHECK_TOLERANCE,
) -> dict:
	"""Recompute from costs + rates and compare against declared DAI values.

	`costs` carries ``fob``/``freight``/``insurance`` accumulated from the
	linked source documents; `rates` carries the DAI/tariff percentages;
	`declared` carries the DAI amounts. Returns ``computed`` (T1 chain),
	``differences`` (empty when matched), and ``matched``. Any difference
	above `tolerance` fails loud naming every culprit field.
	"""
	computed = compute_import_taxes(
		fob=(costs or {}).get("fob"),
		freight=(costs or {}).get("freight"),
		insurance=(costs or {}).get("insurance"),
		ad_valorem_rate_pct=(rates or {}).get("ad_valorem"),
		fodinfa_rate_pct=(rates or {}).get("fodinfa"),
		iva_rate_pct=(rates or {}).get("iva"),
		ice=(costs or {}).get("ice", 0.0),
		other_duties=(costs or {}).get("other_duties", 0.0),
	)
	pairs = (
		("dai_ad_valorem", computed["ad_valorem"]),
		("dai_fodinfa", computed["fodinfa"]),
		("dai_iva", computed["iva"]),
		(
			"dai_total",
			round(
				computed["ad_valorem"]
				+ computed["fodinfa"]
				+ computed["iva"]
				+ computed["ice"]
				+ computed["other_duties"],
				2,
			),
		),
	)
	differences: dict[str, float] = {}
	for field, expected in pairs:
		if field not in (declared or {}):
			raise ValueError(_("Declared DAI field '{}' is required for crosscheck.").format(field))
		delta = round(abs(float(declared[field]) - expected), 2)
		if delta > tolerance:
			differences[field] = delta
	if differences:
		culprits = ", ".join(f"{field} (off by {delta})" for field, delta in differences.items())
		raise ValueError(_("DAI crosscheck mismatch beyond tolerance: {}.").format(culprits))
	return {"computed": computed, "differences": differences, "matched": True}
