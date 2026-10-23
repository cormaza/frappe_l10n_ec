"""Customer-side multi-invoice withholding allocations (received, not emitted).

A customer withholds at payment time and issues ONE slip for MANY of our
sales invoices. This module validates the per-invoice split; settlement
still posts per invoice through `received_settlement` (one JE each, same
remark idempotency). Supplier-side emission (`voucher_flow`) never reads
these records.

Pure core (`check_allocation`) runs on plain data (Ring 1); bench wrappers
(`validate_allocations`, `maxima_for_si`) resolve documents. Amounts must
be capped by each invoice's own maxima — never trusted from input alone.
"""

from l10n_ec.sri.codes import sri_code

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


def check_allocation(allocation: dict, invoices: dict) -> None:
	"""Validate one allocation row against its invoice maxima (pure).

	``allocation`` carries ``sales_invoice``, ``ir_value``, ``iva_value``;
	``invoices`` maps invoice names to ``{customer, company, net_total,
	iva_paid, ir_concepto, iva_concepto, settled, referenced}``. Raises
	`ValueError` naming the broken rule:

	- V0 unknown invoice; V4 customer/company mismatch with its siblings
	  (checked across rows by the caller comparing each row's invoice);
	- V1 invoice already settled or carrying another slip's references;
	- V2 IR leg capped by ``net_total x concepto rate`` (concepto required
	  when the leg is positive);
	- V3 IVA leg capped by ``iva_paid`` (concepto required when positive).
	"""
	from l10n_ec.sri.withholding_concepts import resolve_concepto

	si_name = (allocation or {}).get("sales_invoice") or ""
	invoice = (invoices or {}).get(si_name)
	if invoice is None:
		raise ValueError(_("Allocation references unknown invoice '{}'.").format(si_name))
	ir_value = round(float(allocation.get("ir_value") or 0.0), 2)
	iva_value = round(float(allocation.get("iva_value") or 0.0), 2)
	if ir_value < 0 or iva_value < 0:
		raise ValueError(_("Allocation for '{}' carries negative values.").format(si_name))
	if not ir_value and not iva_value:
		raise ValueError(_("Allocation for '{}' withholds nothing.").format(si_name))
	if invoice.get("settled"):
		raise ValueError(
			_("Invoice '{}' already has a settlement entry; refusing a second slip.").format(si_name)
		)
	if invoice.get("referenced"):
		raise ValueError(_("Invoice '{}' already carries another slip's references.").format(si_name))
	if ir_value:
		concepto = (invoice.get("ir_concepto") or "").strip()
		if not concepto:
			raise ValueError(_("Invoice '{}' needs an IR concepto before withholding IR.").format(si_name))
		impuesto, rate, _description = resolve_concepto(concepto)
		if impuesto != "1":
			raise ValueError(_("IR withholding needs an IR concepto, got '{}'.").format(concepto))
		top = round(float(invoice.get("net_total") or 0.0) * rate / 100, 2)
		if ir_value - top > 0.005:
			raise ValueError(
				_("IR {} on '{}' exceeds its base {} x {}%.").format(
					ir_value, si_name, invoice.get("net_total"), rate
				)
			)
	if iva_value:
		iva_concepto = (invoice.get("iva_concepto") or "").strip()
		if not iva_concepto:
			raise ValueError(_("Invoice '{}' needs an IVA concepto before withholding IVA.").format(si_name))
		top = round(float(invoice.get("iva_paid") or 0.0), 2)
		if iva_value - top > 0.005:
			raise ValueError(_("IVA {} on '{}' exceeds its paid IVA {}.").format(iva_value, si_name, top))


def check_siblings(allocations: list, invoices: dict) -> None:
	"""Every allocated invoice shares one customer and company (pure, V4)."""
	customers = set()
	companies = set()
	for allocation in allocations or []:
		invoice = (invoices or {}).get((allocation or {}).get("sales_invoice") or "")
		if invoice is None:
			continue
		customers.add(invoice.get("customer"))
		companies.add(invoice.get("company"))
	if len(customers) > 1:
		raise ValueError(_("Allocations mix customers {}; one slip, one customer.").format(sorted(customers)))
	if len(companies) > 1:
		raise ValueError(_("Allocations mix companies {}; one slip, one company.").format(sorted(companies)))


def _invoice_context(si_name: str) -> dict | None:
	"""Bench-only invoice maxima + flags for one sales invoice."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		return None
	if not frappe.db.exists("Sales Invoice", si_name):
		return None
	si = frappe.get_doc("Sales Invoice", si_name)
	from l10n_ec.ecuador_localization.received_settlement import _existing_settlement
	from l10n_ec.ecuador_localization.voucher_flow import base_lines, map_line_taxes

	mapped = [map_line_taxes(line) for line in base_lines(si)]
	iva_paid = round(
		sum(
			tax.get("value", 0.0)
			for line in mapped
			for tax in line.get("taxes", [])
			if tax.get("code") == "2"
		),
		2,
	)
	return {
		"customer": si.get("customer"),
		"company": si.get("company"),
		"net_total": si.get("net_total"),
		"iva_paid": iva_paid,
		"ir_concepto": si.get("sri_ir_concepto"),
		"iva_concepto": sri_code(si.get("sri_iva_concepto")),
		"settled": _existing_settlement(si_name) is not None,
		"referenced": bool(si.get("sri_received_retencion_number")),
	}


def validate_allocations(doc) -> None:
	"""Validate every allocation row of a received batch (bench only)."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to validate allocations.")
	rows = doc.get("allocations") or []
	if not rows:
		raise ValueError(_("A received batch needs at least one allocation."))
	invoices = {}
	for row in rows:
		context = _invoice_context(row.get("sales_invoice") or "")
		if context is None:
			raise ValueError(
				_("Allocation references unknown invoice '{}'.").format(row.get("sales_invoice"))
			)
		invoices[row.get("sales_invoice")] = context
	try:
		check_siblings([{"sales_invoice": row.get("sales_invoice")} for row in rows], invoices)
		for row in rows:
			check_allocation(
				{
					"sales_invoice": row.get("sales_invoice"),
					"ir_value": row.get("ir_value"),
					"iva_value": row.get("iva_value"),
				},
				invoices,
			)
		if doc.get("customer") and any(
			(entry or {}).get("customer") != doc.get("customer") for entry in invoices.values()
		):
			raise ValueError(
				_("Allocations must belong to the batch customer '{}'.").format(doc.get("customer"))
			)
		if doc.get("company") and any(
			(entry or {}).get("company") != doc.get("company") for entry in invoices.values()
		):
			raise ValueError(
				_("Allocations must belong to the batch company '{}'.").format(doc.get("company"))
			)
	except ValueError as exc:
		frappe.throw(str(exc))
		raise
