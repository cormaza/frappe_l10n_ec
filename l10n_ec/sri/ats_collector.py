"""Monthly ATS collector: aggregate one posted fiscal month into SRI sections.

Pure Python, no frappe: Ring 1 tests inject a synthetic ``reader`` and never
touch the database. Rendering (XML/zip plus ``ats.xsd`` validation) belongs
to T2; this module only aggregates plain dicts shaped like the ``ats.xsd``
sections ``compras``/``ventas``/``exportaciones``/``anulados``.

Reader interface (injected callable, documented here as the contract)::

    reader(company: str, year: int, month: int) -> {
        "purchases": [purchase, ...],
        "sales": [sale, ...],
        "exports": [export, ...],
        "cancelled": [cancelled, ...],
    }

Each entry is a plain dict. Missing section keys behave as empty lists.
The reader owns the posted filter: only submitted Purchase/Sales Invoices
(docstatus 1), authorized/settled sales, and cancelled SRI-numbered docs
reach the collector. Rows that still carry an explicit non-submitted
``docstatus`` are skipped defensively.

Purchase shape (submitted Purchase Invoice plus linked 07 voucher data)::

    {
        "supplier_id_type": "04",
        "supplier_id": "1790016919001",
        "supplier_name": "...",
        "related_party": "NO",
        "sustento_code": "02",
        "doc_code": "01",
        "sri_number": "001-001-000000123",
        "issue_date": "15/03/2026",
        "register_date": "20/03/2026",
        "auth_number": "1234567890",
        "taxes": [{"template": "Ecuador VAT 15% - Purchases", "base": 1000.0, "value": 150.0}, ...]
        | [{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0}, ...],
        "ice_amount": 0.0,
        "payments": [{"method": "01", "amount": 1150.0}],
        "withholdings": [{"concepto": "303", "base": 1000.0, "rate": 10.0, "value": 100.0}, ...],
        "retencion": {"number": "001-001-000000007", "authorization": "1234567890", "date": "25/03/2026"},
    }

Multi-sustento 07 vouchers arrive pre-grouped per purchase through
``voucher_flow.group_withholdings_by_sustento``: the collector treats each
purchase's ``withholdings`` as that sustento's ``air`` block, and any row
may override ``sustento_code`` per withholding entry.

Sale shape (submitted Sales Invoice, authorized/settled)::

    {
        "customer_id_type": "04", "customer_id": "1790016919001",
        "customer_name": "...", "doc_code": "01", "emission": "E",
        "sri_number": "001-001-000000123",
        "issue_date": "15/03/2026", "auth_number": "1234567890",
        "taxes": [...same shapes as purchases...],
        "ice_amount": 0.0,
        "payments": [{"method": "19", "amount": 1150.0}],
        "received": {"retencion_number": "001-002-000000009",
                     "authorization": "0987654321", "date": "28/03/2026",
                     "access_key": "<49 digits>",
                     "iva_value": 45.0, "renta_value": 20.0},
    }

``received`` mirrors ``received_settlement`` (TDS asset accounts 1010501/
1010502 plus the customer-issued retencion references) and feeds the
ventas credit (``valorRetIva``/``valorRetRenta``). One output row covers
one posted invoice (``numeroComprobantes`` 1); T2 renders rows as-is.

Export shape (passthrough; empty list when the month has no exports)::

    {
        "exportacion_de": "01",
        "doc_code": "01",
        "sri_number": "001-001-000000123",
        "issue_date": "15/03/2026",
        "auth_number": "1234567890",
        "embarque_date": "16/03/2026",
        "fob_value": 5000.0,
        "voucher_fob_value": 5000.0,
    }

Cancelled shape (feeds ``anulados`` with its SRI numbers; a range is one
row per doc with ``secuencialInicio == secuencialFin``)::

    {"doc_code": "01", "sri_number": "001-001-000000124", "auth_number": "1234567890"}

Aggregation rules:

* IVA bases split by SRI rate code (resolved via ``tax_codes`` when the
  input carries template titles): rate ``6`` (no object) feeds
  ``baseNoGraIva``, rate ``0`` feeds ``baseImponible``, taxed rates
  (``2``/``3``/``4``/``8``) feed ``baseImpGrav``, rate ``7`` (exempt)
  feeds ``baseImpExe``. ``montoIva`` sums IVA (impuesto ``2``) values.
* ICE rows pass ``ice_amount`` through as ``montoIce`` unchanged: ICE
  tariffs stay user-side per the roadmap, this module never computes them.
* Payment codes default to ``01`` when the doc carries none; every code
  resolves through Tabla 24 and unknown codes fail loud.
* Withholding ``concepto`` codes resolve through the concepto table:
  unknown codes fail loud, impuesto ``9`` rows fail loud (ATS scope,
  never an XML ``codigoRetencion``), and rated conceptos must carry the
  official rate (never guess). IR rows (impuesto ``1``) become ``air``
  entries; IVA rows (impuesto ``2``) accumulate the retained-value
  buckets by rate (10/20/30/50/70/100).
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.payment_methods import resolve_payment_method
from l10n_ec.sri.tax_codes import tax_codes_for_template
from l10n_ec.sri.voucher_states import SriVoucherError
from l10n_ec.sri.withholding_concepts import NON_EMITTABLE_IMPUESTOS, resolve_concepto

DEFAULT_PAYMENT_METHOD = "01"
DEFAULT_SUSTENTO_CODE = "02"

#: IVA retained-value bucket by withholding rate (impuesto '2' conceptos).
IVA_RETAINED_BUCKETS = {
	10.0: "valRetBien10",
	20.0: "valRetServ20",
	30.0: "valorRetBienes",
	50.0: "valRetServ50",
	70.0: "valorRetServicios",
	100.0: "valRetServ100",
}

#: IVA rate codes that feed the taxed base (gravada). '6' is no-object,
#: '0' is zero-rate, '7' is exempt; anything else taxes the base.
TAXED_RATE_CODES = frozenset({"2", "3", "4", "8"})


def collect_month(company: str, year: int, month: int, reader) -> dict:
	"""Aggregate one posted fiscal month into ATS sections as plain data.

	``reader(company, year, month)`` returns the month docs mapping
	(``purchases``/``sales``/``exports``/``cancelled``); absent sections
	read as empty lists. Returns ``{"compras": [...], "ventas": [...],
	"exportaciones": [...], "anulados": [...]}``.
	"""
	_validate_period(company, year, month)
	month_docs = reader(company, year, month) or {}
	purchases = month_docs.get("purchases") or []
	sales = month_docs.get("sales") or []
	exports = month_docs.get("exports") or []
	cancelled = month_docs.get("cancelled") or []
	return {
		"compras": [collect_purchase(doc) for doc in purchases if _is_posted(doc)],
		"ventas": [collect_sale(doc) for doc in sales if _is_posted(doc)],
		"exportaciones": [collect_export(doc) for doc in exports],
		"anulados": [collect_cancelled(doc) for doc in cancelled],
	}


def _validate_period(company: str, year: int, month: int) -> None:
	"""Fail loud on an unusable fiscal period before touching the reader."""
	if not company:
		raise SriVoucherError(_("ATS collection needs a company for '{}-{:02d}'.").format(year, month))
	if not isinstance(year, int) or year < 2000 or year > 9999:
		raise SriVoucherError(_("ATS collection year '{}' is out of range.").format(year))
	if not isinstance(month, int) or month < 1 or month > 12:
		raise SriVoucherError(_("ATS collection month '{}' is out of range.").format(month))


def _is_posted(doc: dict) -> bool:
	"""Trust the reader's posted filter; skip explicit non-submitted rows."""
	status = doc.get("docstatus", 1)
	return status == 1


def split_sri_number(sri_number: str) -> tuple:
	"""Split ``001-001-000000123`` into establishment/point/sequential."""
	parts = (sri_number or "").split("-")
	if len(parts) != 3 or not all(part.isdigit() for part in parts):
		raise SriVoucherError(_("ATS document number '{}' is not a SRI number.").format(sri_number))
	return (parts[0], parts[1], parts[2])


def resolve_taxes(taxes: list) -> list:
	"""Normalize tax rows to ``(code, rate_code, base, value)`` SRI shapes.

	Rows may carry template titles (resolved via ``tax_codes``) or explicit
	SRI codes. Unknown templates and codes fail loud instead of guessing.
	"""
	resolved = []
	for tax in taxes or []:
		if "template" in tax:
			code, rate_code = tax_codes_for_template(tax["template"])
		else:
			code, rate_code = tax["code"], tax["rate_code"]
		resolved.append(
			{
				"code": code,
				"rate_code": rate_code,
				"base": round(float(tax.get("base", 0.0)), 2),
				"value": round(float(tax.get("value", 0.0)), 2),
			}
		)
	return resolved


def split_iva_bases(taxes: list) -> dict:
	"""Split resolved IVA taxes into ATS base buckets plus ``montoIva``."""
	bases = {
		"baseNoGraIva": 0.0,
		"baseImponible": 0.0,
		"baseImpGrav": 0.0,
		"baseImpExe": 0.0,
		"montoIva": 0.0,
	}
	for tax in taxes:
		if tax["code"] != "2":
			continue
		base = round(float(tax["base"]), 2)
		value = round(float(tax["value"]), 2)
		rate_code = tax["rate_code"]
		if rate_code == "6":
			bases["baseNoGraIva"] = round(bases["baseNoGraIva"] + base, 2)
		elif rate_code == "0":
			bases["baseImponible"] = round(bases["baseImponible"] + base, 2)
		elif rate_code == "7":
			bases["baseImpExe"] = round(bases["baseImpExe"] + base, 2)
		else:
			bases["baseImpGrav"] = round(bases["baseImpGrav"] + base, 2)
		bases["montoIva"] = round(bases["montoIva"] + value, 2)
	return bases


def resolve_payment_codes(payments: list | None, doc_number: str) -> list:
	"""Return validated Tabla 24 payment codes, defaulting to ``01``."""
	if not payments:
		return [DEFAULT_PAYMENT_METHOD]
	codes = []
	for payment in payments:
		code = payment.get("method", DEFAULT_PAYMENT_METHOD)
		resolve_payment_method(code)
		codes.append(code)
	return codes


def split_withholdings(withholdings: list) -> tuple:
	"""Split withholding rows into ``(air, iva_buckets)`` ATS shapes.

	IR rows (impuesto ``1``) become ``air`` entries; IVA rows (impuesto
	``2``) accumulate the retained-value buckets by rate. Unknown
	conceptos, impuesto ``9`` scope codes, rate mismatches against rated
	conceptos, and unmapped IVA rates all fail loud.
	"""
	air = []
	iva_buckets = {bucket: 0.0 for bucket in IVA_RETAINED_BUCKETS.values()}
	for row in withholdings or []:
		concepto = row["concepto"]
		impuesto, official_rate, _description = resolve_concepto(concepto)
		if impuesto in NON_EMITTABLE_IMPUESTOS:
			raise SriVoucherError(
				_("SRI withholding concepto '{}' is ATS scope and has no XML retention row.").format(concepto)
			)
		rate = round(float(row.get("rate", 0.0)), 2)
		base = round(float(row.get("base", 0.0)), 2)
		value = round(float(row.get("value", 0.0)), 2)
		if official_rate is not None and rate != round(float(official_rate), 2):
			raise SriVoucherError(
				_("SRI withholding concepto '{}' carries rate '{}' but the official rate is '{}'.").format(
					concepto, row.get("rate"), official_rate
				)
			)
		if impuesto == "1":
			air.append(
				{
					"codRetAir": concepto,
					"baseImpAir": base,
					"porcentajeAir": rate,
					"valRetAir": value,
				}
			)
		else:
			bucket = IVA_RETAINED_BUCKETS.get(rate)
			if bucket is None:
				raise SriVoucherError(
					_("SRI IVA withholding concepto '{}' has no ATS bucket for rate '{}'.").format(
						concepto, row.get("rate")
					)
				)
			iva_buckets[bucket] = round(iva_buckets[bucket] + value, 2)
	return (air, iva_buckets)


def collect_purchase(doc: dict) -> dict:
	"""Aggregate one submitted Purchase Invoice into a ``compras`` row."""
	sri_number = doc.get("sri_number", "")
	establishment, point, sequential = split_sri_number(sri_number)
	taxes = resolve_taxes(doc.get("taxes"))
	bases = split_iva_bases(taxes)
	air, iva_buckets = split_withholdings(doc.get("withholdings"))
	payments = resolve_payment_codes(doc.get("payments"), sri_number)
	row = {
		"codSustento": doc.get("sustento_code", DEFAULT_SUSTENTO_CODE),
		"tpIdProv": doc.get("supplier_id_type", ""),
		"idProv": doc.get("supplier_id", ""),
		"tipoComprobante": doc.get("doc_code", ""),
		"denoProv": doc.get("supplier_name", ""),
		"parteRel": doc.get("related_party", "NO"),
		"fechaRegistro": doc.get("register_date", doc.get("issue_date", "")),
		"establecimiento": establishment,
		"puntoEmision": point,
		"secuencial": sequential,
		"fechaEmision": doc.get("issue_date", ""),
		"autorizacion": doc.get("auth_number", ""),
		**bases,
		"montoIce": round(float(doc.get("ice_amount", 0.0)), 2),
		**iva_buckets,
		"formasDePago": payments,
		"air": air,
	}
	retencion = doc.get("retencion") or {}
	if retencion.get("number"):
		estab, pto, sec = split_sri_number(retencion["number"])
		row.update(
			{
				"estabRetencion1": estab,
				"ptoEmiRetencion1": pto,
				"secRetencion1": sec,
				"autRetencion1": retencion.get("authorization", ""),
				"fechaEmiRet1": retencion.get("date", ""),
			}
		)
	return row


def collect_sale(doc: dict) -> dict:
	"""Aggregate one submitted Sales Invoice into a ``ventas`` row."""
	sri_number = doc.get("sri_number", "")
	taxes = resolve_taxes(doc.get("taxes"))
	bases = split_iva_bases(taxes)
	payments = resolve_payment_codes(doc.get("payments"), sri_number)
	received = doc.get("received") or {}
	row = {
		"tpIdCliente": doc.get("customer_id_type", ""),
		"idCliente": doc.get("customer_id", ""),
		"denoCli": doc.get("customer_name", ""),
		"tipoComprobante": doc.get("doc_code", ""),
		"tipoEmision": doc.get("emission", "E"),
		"numeroComprobantes": 1,
		"baseNoGraIva": bases["baseNoGraIva"],
		"baseImponible": bases["baseImponible"],
		"baseImpGrav": bases["baseImpGrav"],
		"montoIva": bases["montoIva"],
		"montoIce": round(float(doc.get("ice_amount", 0.0)), 2),
		"valorRetIva": round(float(received.get("iva_value", 0.0)), 2),
		"valorRetRenta": round(float(received.get("renta_value", 0.0)), 2),
		"formasDePago": payments,
	}
	if received.get("retencion_number"):
		row.update(
			{
				"received_number": received.get("retencion_number", ""),
				"received_authorization": received.get("authorization", ""),
				"received_date": received.get("date", ""),
				"received_access_key": received.get("access_key", ""),
			}
		)
	return row


def collect_export(doc: dict) -> dict:
	"""Aggregate one export voucher into an ``exportaciones`` row."""
	establishment, point, sequential = split_sri_number(doc.get("sri_number", ""))
	return {
		"exportacionDe": doc.get("exportacion_de", ""),
		"tipoComprobante": doc.get("doc_code", ""),
		"fechaEmbarque": doc.get("embarque_date", ""),
		"valorFOB": round(float(doc.get("fob_value", 0.0)), 2),
		"valorFOBComprobante": round(float(doc.get("voucher_fob_value", doc.get("fob_value", 0.0))), 2),
		"establecimiento": establishment,
		"puntoEmision": point,
		"secuencial": sequential,
		"autorizacion": doc.get("auth_number", ""),
		"fechaEmision": doc.get("issue_date", ""),
	}


def collect_cancelled(doc: dict) -> dict:
	"""Aggregate one cancelled doc into an ``anulados`` range row."""
	establishment, point, sequential = split_sri_number(doc.get("sri_number", ""))
	return {
		"tipoComprobante": doc.get("doc_code", ""),
		"establecimiento": establishment,
		"puntoEmision": point,
		"secuencialInicio": sequential,
		"secuencialFin": sequential,
		"autorizacion": doc.get("auth_number", ""),
	}
