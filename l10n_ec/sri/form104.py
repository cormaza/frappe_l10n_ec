"""Monthly Form 104 (IVA) collector: aggregate one posted fiscal month into SRI casilleros.

Pure Python, no frappe: Ring 1 tests inject a plain ``ledger`` dict and never
touch the database. The caller (bench Script Report or tests) resolves every
SRI code before calling: tax rows carry ``(code, rate_code)`` pairs, IVA
deduction rows carry their withholding rate, settlement lines carry their TDS
asset account number. Rendering (the Frappe Script Report table plus the SRI
portal upload) belongs to the report layer; this module only aggregates.

Ledger interface (plain data, documented here as the contract)::

    {
        "sales_taxes": [{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0}, ...],
        "purchase_taxes": [{"code": "2", "rate_code": "4", "base": 2000.0, "value": 300.0}, ...],
        "iva_deduction_rows": [{"rate": 30.0, "amount": 90.0}, ...],
        "settlements": [{"account_number": "1010501", "debit": 45.0}, ...],
        "received_refs": [{"number": "001-002-000000009", "authorization": "0987654321",
                           "date": "28/03/2026", "iva_value": 45.0, "renta_value": 20.0}, ...],
    }

Missing section keys behave as empty lists. The bench report owns the posted
filter: only submitted Sales/Purchase Invoices and Journal Entries of the
month reach the collector.

Aggregation rules:

* VAT bases split by SRI rate code (``tax_codes``): nonzero rates
  (``2``/``3``/``4``) feed ventas ``401``/``411``/``421`` and compras
  ``500``/``510``/``520``; differentiated ``8`` feeds ``425``/``435``/``445``
  and ``540``/``550``/``560``; zero-rate ``0`` feeds ``403``/``413`` and
  ``507``/``517``; no-object ``6`` and exempt ``7`` feed ``431``/``441`` and
  ``531``/``541``/``532``/``542``. Fixed-asset, import, export,
  variable-rate, and carryover boxes stay zero: the ledger carries no input
  that distinguishes them. Known non-VAT impuesto codes (``3`` ICE,
  ``5`` IRBPNR) are ignored; anything else fails loud.
* IVA deduction rows (the ``Deduct`` rows from ``validation``,
  account ``2010708``) are withholdings we effected as agent: each row feeds
  the ``721``-``731`` box of its rate (10/20/30/50/70/100). Zero-amount rows
  contribute nothing; nonzero amounts with unmapped rates fail loud.
* Settlement lines (``received_settlement`` Journal Entries) are customer
  withholdings effected on us: ``1010501`` (IVA) debits feed ``609``,
  ``1010502`` (IR) debits are carried as ``received_ir_credit`` (Form 104
  has no IR casillero; Form 103 owns that credit). Unknown asset numbers
  fail loud.
* Received references (customer-issued retencion slips) are validated and
  recorded as ``received_refs`` for the report traceability section; they
  never double-count ``609`` (the posted settlement debits are the single
  source of truth).
* Settlement follows the OCA reference (``oca_104_collector``): cash versus
  credit has no payment-term input in the ledger, so every nonzero-rated
  sale settles cash (``480``/``484``), ``485`` is ``482``-``484``, and
  ``499`` is ``483``+``484``. ``563``/``564``/``565`` apply the
  proportionality factor (``1.0`` when ``419`` is zero), ``601``/``602`` are
  mutually exclusive, ``620`` is the SRI formula, ``699`` is ``620``+``621``,
  ``801`` is ``799`` (no ``800``/``802`` carryover input), and ``859`` is
  ``699``+``801``. Prior-period and case-file boxes (``483``,
  ``603``-``608``, ``610``-``619``, ``621``, ``623``-``625``, ``492``)
  default to zero and travel with the caller when the report grows inputs.
* Every casillero in :data:`FORM104_BOXES` is present even when zero
  (empty-boxes pattern), in stable form order.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.ecuador_localization.received_settlement import (
	IR_CREDIT_ACCOUNT_NUMBER,
	IVA_CREDIT_ACCOUNT_NUMBER,
)
from l10n_ec.sri.voucher_states import SriVoucherError

#: SRI VAT rate codes aggregated as nonzero-rated (12/14/15%).
NONZERO_RATE_CODES = frozenset({"2", "3", "4"})
#: Known non-VAT impuesto codes ignored by the VAT aggregation (no 104 boxes).
NON_VAT_CODES = frozenset({"3", "5"})

#: IVA deduction rate to agente-de-retencion box (SRI Tabla 23 rates).
RETENTION_BOX_BY_RATE = {
	10.0: "721",
	20.0: "723",
	30.0: "725",
	50.0: "727",
	70.0: "729",
	100.0: "731",
}

#: Casilleros in stable SRI form order (every box the collector owns).
_BOX_ORDER = (
	"401",
	"402",
	"403",
	"404",
	"405",
	"406",
	"407",
	"408",
	"409",
	"410",
	"411",
	"412",
	"413",
	"414",
	"415",
	"416",
	"417",
	"418",
	"419",
	"420",
	"421",
	"422",
	"423",
	"424",
	"425",
	"429",
	"430",
	"431",
	"434",
	"435",
	"441",
	"442",
	"443",
	"444",
	"445",
	"453",
	"454",
	"500",
	"501",
	"502",
	"503",
	"504",
	"505",
	"506",
	"507",
	"508",
	"509",
	"510",
	"511",
	"512",
	"513",
	"514",
	"515",
	"516",
	"517",
	"518",
	"519",
	"520",
	"521",
	"522",
	"523",
	"524",
	"525",
	"526",
	"527",
	"529",
	"530",
	"531",
	"532",
	"533",
	"534",
	"535",
	"540",
	"541",
	"542",
	"543",
	"544",
	"545",
	"550",
	"554",
	"555",
	"560",
	"480",
	"481",
	"482",
	"483",
	"484",
	"485",
	"486",
	"487",
	"499",
	"563",
	"564",
	"565",
	"601",
	"602",
	"603",
	"604",
	"605",
	"606",
	"607",
	"608",
	"609",
	"610",
	"611",
	"612",
	"613",
	"614",
	"615",
	"617",
	"618",
	"619",
	"620",
	"621",
	"623",
	"624",
	"625",
	"492",
	"699",
	"721",
	"723",
	"725",
	"727",
	"729",
	"731",
	"799",
	"801",
	"859",
)

#: Every casillero the collector owns (empty-boxes invariant).
FORM104_BOXES = frozenset(_BOX_ORDER)


def collect_104(ledger: dict, year: int, month: int) -> dict:
	"""Aggregate one posted fiscal month into Form 104 casilleros plus traceability.

	``ledger`` carries the month plain data (``sales_taxes``,
	``purchase_taxes``, ``iva_deduction_rows``, ``settlements``,
	``received_refs``); absent sections read as empty lists. Returns the
	casillero mapping (every box in :data:`FORM104_BOXES`, rounded) plus
	``received_refs`` (normalized references) and ``received_ir_credit``
	(no IVA casillero; carried for Form 103).
	"""
	_validate_period(year, month)
	ledger = ledger or {}
	sales = _aggregate_vat(ledger.get("sales_taxes") or [], _sales_boxes)
	purchases = _aggregate_vat(ledger.get("purchase_taxes") or [], _purchase_boxes)
	computed: dict = {}
	computed.update(sales)
	computed.update(purchases)
	computed.update(_settle(sales, purchases, ledger))
	return {**{box: round(float(computed.get(box, 0.0)), 2) for box in _BOX_ORDER},
		"received_refs": _normalize_refs(ledger.get("received_refs") or []),
		"received_ir_credit": round(float(computed.get("received_ir_credit", 0.0)), 2)}


def _validate_period(year: int, month: int) -> None:
	"""Fail loud on an unusable fiscal period before touching the ledger."""
	if not isinstance(year, int) or year < 2000 or year > 9999:
		raise SriVoucherError(_("Form 104 collection year '{}' is out of range.").format(year))
	if not isinstance(month, int) or month < 1 or month > 12:
		raise SriVoucherError(_("Form 104 collection month '{}' is out of range.").format(month))


def _aggregate_vat(rows: list, splitter) -> dict:
	"""Aggregate caller-resolved tax rows into section boxes via ``splitter``."""
	boxes: dict = {}
	for row in rows:
		code = row.get("code")
		rate_code = row.get("rate_code")
		if code != "2":
			if code in NON_VAT_CODES:
				continue
			raise SriVoucherError(_("Form 104 tax code '{}' is not a SRI impuesto.").format(code))
		base = round(float(row.get("base", 0.0)), 2)
		value = round(float(row.get("value", 0.0)), 2)
		gross_box, net_box, tax_box = splitter(rate_code)
		boxes[gross_box] = round(boxes.get(gross_box, 0.0) + base, 2)
		boxes[net_box] = round(boxes.get(net_box, 0.0) + base, 2)
		boxes[tax_box] = round(boxes.get(tax_box, 0.0) + value, 2)
	return boxes


def _sales_boxes(rate_code: str) -> tuple:
	"""Map a VAT rate code to its ventas ``(gross, net, tax)`` boxes."""
	if rate_code in NONZERO_RATE_CODES:
		return ("401", "411", "421")
	if rate_code == "8":
		return ("425", "435", "445")
	if rate_code == "0":
		return ("403", "413", "421")
	if rate_code in ("6", "7"):
		return ("431", "441", "421")
	raise SriVoucherError(_("Form 104 VAT rate code '{}' is not a SRI rate.").format(rate_code))


def _purchase_boxes(rate_code: str) -> tuple:
	"""Map a VAT rate code to its compras ``(gross, net, tax)`` boxes."""
	if rate_code in NONZERO_RATE_CODES:
		return ("500", "510", "520")
	if rate_code == "8":
		return ("540", "550", "560")
	if rate_code == "0":
		return ("507", "517", "520")
	if rate_code == "6":
		return ("531", "541", "520")
	if rate_code == "7":
		return ("532", "542", "520")
	raise SriVoucherError(_("Form 104 VAT rate code '{}' is not a SRI rate.").format(rate_code))


def _settle(sales: dict, purchases: dict, ledger: dict) -> dict:
	"""Compute totals, liquidation, perception, and retention boxes."""
	boxes: dict = {}
	boxes["409"] = sum(sales.get(box, 0.0) for box in ("401", "402", "403", "404", "405", "406", "407", "408", "410", "425"))
	boxes["419"] = sum(sales.get(box, 0.0) for box in ("411", "412", "413", "414", "415", "416", "417", "418", "420", "435"))
	boxes["429"] = (
		sum(sales.get(box, 0.0) for box in ("421", "422", "423", "430", "445"))
		- sales.get("424", 0.0)
	)
	boxes["509"] = sum(
		purchases.get(box, 0.0)
		for box in ("500", "501", "502", "503", "504", "505", "506", "507", "508", "530", "540")
	)
	boxes["519"] = sum(
		purchases.get(box, 0.0)
		for box in ("510", "511", "512", "513", "514", "515", "516", "517", "518", "533", "550")
	)
	boxes["529"] = (
		sum(purchases.get(box, 0.0) for box in ("520", "521", "522", "523", "524", "525", "526", "534", "560"))
		- purchases.get("527", 0.0)
	)
	nonzero_base = sum(sales.get(box, 0.0) for box in ("401", "402", "410", "425"))
	nonzero_tax = sum(sales.get(box, 0.0) for box in ("421", "422", "430", "445"))
	boxes["480"] = nonzero_base
	boxes["481"] = 0.0
	boxes["482"] = boxes["429"]
	boxes["483"] = 0.0
	boxes["484"] = nonzero_tax
	boxes["485"] = boxes["482"] - boxes["484"]
	boxes["499"] = boxes["483"] + boxes["484"]
	total_net = boxes["419"]
	if total_net:
		boxes["563"] = (
			sum(sales.get(box, 0.0) for box in ("411", "412", "420", "415", "416", "417", "418"))
			/ total_net
		)
	else:
		boxes["563"] = 1.0
	credit_base = (
		sum(purchases.get(box, 0.0) for box in ("520", "521", "534", "560", "523", "524", "525", "526"))
		- purchases.get("527", 0.0)
	)
	boxes["564"] = credit_base * boxes["563"]
	boxes["565"] = credit_base - boxes["564"]
	difference = boxes["499"] - boxes["564"]
	boxes["601"] = difference if difference > 0 else 0.0
	boxes["602"] = -difference if difference < 0 else 0.0
	iva_received, ir_received = _aggregate_settlements(ledger.get("settlements") or [])
	boxes["609"] = iva_received
	boxes["received_ir_credit"] = ir_received
	boxes["620"] = (
		boxes["601"]
		- boxes["602"]
		- boxes.get("603", 0.0)
		- boxes.get("604", 0.0)
		- boxes.get("605", 0.0)
		- boxes.get("606", 0.0)
		- boxes.get("607", 0.0)
		- boxes.get("608", 0.0)
		- boxes["609"]
		+ boxes.get("610", 0.0)
		+ boxes.get("611", 0.0)
		+ boxes.get("612", 0.0)
		+ boxes.get("613", 0.0)
		+ boxes.get("614", 0.0)
	)
	boxes["699"] = boxes["620"] + boxes.get("621", 0.0)
	withheld = _aggregate_deductions(ledger.get("iva_deduction_rows") or [])
	boxes.update(withheld)
	boxes["799"] = sum(withheld.get(box, 0.0) for box in RETENTION_BOX_BY_RATE.values())
	boxes["801"] = boxes["799"]
	boxes["859"] = boxes["699"] + boxes["801"]
	return boxes


def _aggregate_settlements(rows: list) -> tuple:
	"""Split settlement debits into ``(iva_received, ir_received)`` totals."""
	iva_received = 0.0
	ir_received = 0.0
	for row in rows:
		number = row.get("account_number")
		debit = round(float(row.get("debit", 0.0)), 2)
		if number == IVA_CREDIT_ACCOUNT_NUMBER:
			iva_received = round(iva_received + debit, 2)
		elif number == IR_CREDIT_ACCOUNT_NUMBER:
			ir_received = round(ir_received + debit, 2)
		else:
			raise SriVoucherError(
				_("Form 104 settlement account '{}' is not a received-withholding asset.").format(number)
			)
	return (iva_received, ir_received)


def _aggregate_deductions(rows: list) -> dict:
	"""Map IVA deduction rows to their ``721``-``731`` retention boxes."""
	boxes: dict = {}
	for row in rows:
		amount = round(float(row.get("amount", 0.0)), 2)
		if not amount:
			continue
		rate = round(float(row.get("rate", 0.0)), 2)
		box = RETENTION_BOX_BY_RATE.get(rate)
		if box is None:
			raise SriVoucherError(
				_("Form 104 IVA deduction rate '{}' has no retention box.").format(row.get("rate"))
			)
		boxes[box] = round(boxes.get(box, 0.0) + amount, 2)
	return boxes


def _normalize_refs(rows: list) -> list:
	"""Validate and normalize customer-issued retencion references."""
	refs = []
	for row in rows:
		number = (row.get("number") or "").strip()
		if not number:
			raise SriVoucherError(_("Form 104 received reference needs a document number."))
		refs.append(
			{
				"number": number,
				"authorization": row.get("authorization") or "",
				"date": row.get("date") or "",
				"iva_value": round(float(row.get("iva_value", 0.0)), 2),
				"renta_value": round(float(row.get("renta_value", 0.0)), 2),
			}
		)
	return refs
