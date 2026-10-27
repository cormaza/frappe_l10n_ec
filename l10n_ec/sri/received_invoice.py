"""Map received SRI factura XML into draft Purchase Invoice data (pure Python).

A1 scope: facturas (01) only. The caller supplies the company context
the XML cannot carry: which stocked item receives the lines, which
sustento classifies them, and the company's own tax templates keyed by
rate. Everything the XML must carry (emisor, number, dates, currency,
per-line taxes) is required fail-loud; nothing is guessed.

Deliberate non-goals: supplier master creation (the bench resolves the
emisor RUC and fails loud asking to create it), ICE/IRBPNR lines
(fail loud, untouched scope), received reembolsos (41s travel their
own path).
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


def _iso_date(sri_date: str | None, field: str) -> str:
	"""Convert a SRI `DD/MM/YYYY` date to ISO; fail loud otherwise."""
	parts = (sri_date or "").strip().split("/")
	if len(parts) != 3 or not all(part.isdigit() for part in parts):
		raise ValueError(_("Received XML date '{}' is not DD/MM/YYYY.").format(sri_date))
	day, month, year = (int(part) for part in parts)
	if not (1 <= month <= 12 and 1 <= day <= 31 and year >= 2000):
		raise ValueError(_("Received XML date '{}' is not a real date.").format(sri_date))
	return f"{year:04d}-{month:02d}-{day:02d}"


def _currency_code(moneda: str | None) -> str:
	"""Map the SRI `moneda` literal to an ERPNext currency code."""
	if (moneda or "").strip().upper() == "DOLAR":
		return "USD"
	raise ValueError(_("Received XML currency '{}' has no ERPNext mapping.").format(moneda))


def _resolve_template(rate: float, templates: list) -> str:
	"""Match one template by exact tarifa; fail loud on zero/ambiguity."""
	matches = [entry["title"] for entry in templates or [] if float(entry.get("rate", -1)) == float(rate)]
	if not matches:
		raise ValueError(
			_("No company tax template matches VAT rate '{}' from the supplier XML.").format(rate)
		)
	if len(matches) > 1:
		raise ValueError(_("Ambiguous tax templates for VAT rate '{}': {}.").format(rate, ", ".join(matches)))
	return matches[0]


def map_received_factura(
	parsed: dict,
	*,
	item_code: str,
	sustento: str,
	templates: list,
) -> dict:
	"""Build a `frappe.get_doc`-ready Purchase Invoice dict from parsed XML.

	`parsed` is the `parse_emitted_xml` factura mapping (with emisor and
	per-line taxes). `item_code` receives every line (the XML description
	travels in each row's description); `sustento` classifies the whole
	voucher; `templates` are the company's own `{"title", "rate"}` rows.
	"""
	if (parsed or {}).get("kind") != "factura":
		raise ValueError(
			_("Received mapper only handles facturas, got '{}'.").format((parsed or {}).get("kind"))
		)
	if parsed.get("reembolsos"):
		raise ValueError(_("Received facturas with reembolsos need the manual path."))
	emisor_ruc = (parsed.get("emisor_ruc") or "").strip()
	if not emisor_ruc:
		raise ValueError(_("Received XML carries no emisor RUC."))
	clave = (parsed.get("clave_acceso") or "").strip()
	if not clave:
		raise ValueError(_("Received XML carries no clave de acceso (offline doubles as auth number)."))
	bill_no = (parsed.get("number") or "").strip()
	if not bill_no:
		raise ValueError(_("Received XML carries no document number."))
	rows = []
	for position, line in enumerate(parsed.get("lines") or [], start=1):
		line_taxes = [tax for tax in (line.get("taxes") or []) if str(tax.get("code")) == "2"]
		if not (line.get("taxes") or []):
			raise ValueError(
				_("Received XML line {} ('{}') has no impuestos block.").format(
					position, line.get("description", "")
				)
			)
		if not line_taxes:
			template = None
		else:
			rates = {float(tax.get("rate", 0.0)) for tax in line_taxes}
			if len(rates) != 1:
				raise ValueError(
					_("Received XML line {} mixes VAT rates: {}.").format(position, sorted(rates))
				)
			template = _resolve_template(next(iter(rates)), templates)
		row: dict = {
			"item_code": item_code,
			"description": line.get("description") or "",
			"qty": float(line.get("qty") or 0),
			"rate": float(line.get("unit_price") or 0),
		}
		if float(line.get("discount") or 0):
			row["discount_amount"] = float(line.get("discount"))
		if template is not None:
			row["item_tax_template"] = template
		rows.append(row)
	if not rows:
		raise ValueError(_("Received XML carries no detail lines."))
	return {
		"doctype": "Purchase Invoice",
		"supplier_tax_id": emisor_ruc,
		"supplier_name": (parsed.get("emisor_name") or "").strip(),
		"bill_no": bill_no,
		"bill_date": _iso_date(parsed.get("issue_date"), "bill_date"),
		"posting_date": _iso_date(parsed.get("issue_date"), "posting_date"),
		"currency": _currency_code(parsed.get("currency")),
		"sri_sustento_code": sustento,
		"sri_supplier_auth_number": clave,
		"update_stock": 0,
		"items": rows,
	}


def resolve_purchase_templates(catalog: list | tuple | None) -> list:
	"""Keep debit-side templates as VAT candidates for received invoices.

	`catalog` rows carry ``title``, ``rate`` and ``account_root_type``.
	Only Asset-rooted templates can hold input VAT (a sales template
	books to a liability and must never price a purchase row). Rows
	without a rate are skipped: the matcher needs one rate per template.
	"""
	kept = []
	for entry in catalog or []:
		if (entry.get("account_root_type") or "").strip() != "Asset":
			continue
		if entry.get("rate") is None:
			continue
		kept.append({"title": entry.get("title"), "rate": float(entry.get("rate"))})
	return kept


def assemble_purchase_invoice(mapped: dict, *, supplier: str, company: str) -> dict:
	"""Turn mapper output into a `frappe.get_doc`-ready Purchase Invoice.

	The document stays a draft: the user reviews taxes, sustento and
	stock behavior before submitting. Supplier and company travel in
	here because the XML cannot carry them.
	"""
	if not supplier:
		raise ValueError(_("A supplier is required to file the received invoice."))
	if not company:
		raise ValueError(_("A company is required to file the received invoice."))
	doc = dict(mapped or {})
	doc["doctype"] = "Purchase Invoice"
	doc["supplier"] = supplier
	doc["company"] = company
	doc.pop("supplier_tax_id", None)
	doc.pop("supplier_name", None)
	return doc
