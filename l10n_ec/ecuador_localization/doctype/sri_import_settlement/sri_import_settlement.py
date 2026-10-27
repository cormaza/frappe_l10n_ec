from __future__ import annotations

from typing import TYPE_CHECKING

try:
	import frappe
	from frappe.model.document import Document
except ImportError:  # pragma: no cover

	class Document:  # type: ignore[no-redef]
		"""Fallback base class when imported outside a Frappe Bench environment."""

		def __init__(self, *args, **kwargs):
			for key, value in kwargs.items():
				setattr(self, key, value)

	frappe = None  # type: ignore[assignment]

from l10n_ec.sri.import_declaration import crosscheck_settlement, parse_declaration_csv
from l10n_ec.sri.import_landed_cost import build_lcv_taxes, select_receipt_document
from l10n_ec.sri.import_links import LINK_DOCTYPES, validate_settlement_links
from l10n_ec.sri.import_settlement import compute_import_taxes


class SRIImportSettlement(Document):
	"""Accumulated import costs toward tax settlement and recosteo.

	T2 owns the link set, T3 the DAI computation, T4 the native Landed
	Cost Voucher prefill. Each layer validates fail loud.
	"""

	if TYPE_CHECKING:
		from frappe.types import DF

		naming_series: DF.Data
		company: DF.Link
		supplier: DF.Link
		purchase_order: DF.Link | None
		purchase_receipt: DF.Link | None
		purchase_invoice: DF.Link | None
		freight_invoice: DF.Link | None
		insurance_invoice: DF.Link | None
		dai_number: DF.Data | None
		dai_date: DF.Date | None
		ad_valorem_rate: DF.Percent | None
		fodinfa_rate: DF.Percent | None
		iva_rate: DF.Percent | None
		ice_amount: DF.Currency | None
		other_duties: DF.Currency | None
		dai_ad_valorem: DF.Currency | None
		dai_fodinfa: DF.Currency | None
		dai_iva: DF.Currency | None
		dai_total: DF.Currency | None
		cif_total: DF.Currency | None
		ad_valorem_amount: DF.Currency | None
		fodinfa_amount: DF.Currency | None
		iva_base: DF.Currency | None
		iva_amount: DF.Currency | None
		landed_cost_voucher: DF.Link | None

	def validate(self) -> None:
		links = {
			role: ((doctype, getattr(self, role, None)) if getattr(self, role, None) else None)
			for role, doctype in LINK_DOCTYPES.items()
		}
		try:
			validate_settlement_links(getattr(self, "company", None), links)
		except ValueError as exc:
			if frappe is not None:
				frappe.throw(str(exc))
			raise
		if frappe is None:  # pragma: no cover
			return
		self._validate_linked_documents(links)
		try:
			self.settle_from(
				self._gather_costs(),
				{
					"ad_valorem": getattr(self, "ad_valorem_rate", None),
					"fodinfa": getattr(self, "fodinfa_rate", None),
					"iva": getattr(self, "iva_rate", None),
				},
				{
					"dai_ad_valorem": getattr(self, "dai_ad_valorem", None),
					"dai_fodinfa": getattr(self, "dai_fodinfa", None),
					"dai_iva": getattr(self, "dai_iva", None),
					"dai_total": getattr(self, "dai_total", None),
				},
			)
		except ValueError as exc:
			frappe.throw(str(exc))
		raise

	def settle_from(self, costs: dict | None, rates: dict | None, declared: dict | None) -> dict:
		"""Compute totals from costs + rates; crosscheck when DAI values exist.

		DB-free so both rings test it: returns the computed chain (and stamps
		it on the document) or ``{}`` when rates are still missing (draft).
		Raises ``ValueError`` on incomplete costs or DAI mismatch.
		"""
		rates = rates or {}
		if any(rates.get(key) is None for key in ("ad_valorem", "fodinfa", "iva")):
			return {}
		costs = dict(costs or {})
		costs.setdefault("ice", float(getattr(self, "ice_amount", None) or 0.0))
		costs.setdefault("other_duties", float(getattr(self, "other_duties", None) or 0.0))
		computed = compute_import_taxes(
			fob=costs.get("fob"),
			freight=costs.get("freight", 0.0),
			insurance=costs.get("insurance", 0.0),
			ad_valorem_rate_pct=rates.get("ad_valorem"),
			fodinfa_rate_pct=rates.get("fodinfa"),
			iva_rate_pct=rates.get("iva"),
			ice=costs.get("ice", 0.0),
			other_duties=costs.get("other_duties", 0.0),
		)
		self.cif_total = computed["cif"]
		self.ad_valorem_amount = computed["ad_valorem"]
		self.fodinfa_amount = computed["fodinfa"]
		self.iva_base = computed["iva_base"]
		self.iva_amount = computed["iva"]
		declared = declared or {}
		if all(
			declared.get(key) is not None for key in ("dai_ad_valorem", "dai_fodinfa", "dai_iva", "dai_total")
		):
			crosscheck_settlement(costs, rates, declared)
		return computed

	def apply_declaration_csv(self, csv_text: str) -> dict:
		"""Primary front-end: transcribe one canonical DAI row onto the form.

		Parses (fail loud), stamps rates/declared/DAI identity, and returns
		the parsed declaration. Saving then recomputes and crosschecks.
		"""
		try:
			parsed = parse_declaration_csv(csv_text)
		except ValueError as exc:
			if frappe is not None:
				frappe.throw(str(exc))
			raise
		self.dai_number = parsed["dai_number"]
		self.dai_date = parsed["dai_date"] or None
		self.ad_valorem_rate = parsed["rates"]["ad_valorem"]
		self.fodinfa_rate = parsed["rates"]["fodinfa"]
		self.iva_rate = parsed["rates"]["iva"]
		self.ice_amount = parsed["duties"]["ice"]
		self.other_duties = parsed["duties"]["other_duties"]
		self.dai_ad_valorem = parsed["declared"]["dai_ad_valorem"]
		self.dai_fodinfa = parsed["declared"]["dai_fodinfa"]
		self.dai_iva = parsed["declared"]["dai_iva"]
		self.dai_total = parsed["declared"]["dai_total"]
		return parsed

	@frappe.whitelist() if frappe else (lambda fn: fn)
	def make_landed_cost_voucher(self) -> str:
		"""Create and submit the native LCV for this settlement (bench only).

		Prefills the receipt (Purchase Receipt preferred, else the exterior
		invoice when it carries Update Stock) and the freight/insurance legs
		as tax rows, lets native code pull items and repost valuation, then
		links the LCV back. Explicit user action; a second call fails loud
		instead of double-costing.
		"""
		existing = getattr(self, "landed_cost_voucher", None)
		if existing:
			msg = f"Settlement already costed by {existing}."
			if frappe is not None:
				frappe.throw(msg)
			raise ValueError(msg)
		if frappe is None:  # pragma: no cover
			raise ValueError("Landed Cost Voucher creation needs a Frappe Bench.")
		if not getattr(self, "name", None):
			frappe.throw("Save the settlement before creating its Landed Cost Voucher.")
		has_update_stock = bool(
			getattr(self, "purchase_invoice", None)
			and frappe.db.get_value("Purchase Invoice", self.purchase_invoice, "update_stock")
		)
		receipt = select_receipt_document(
			getattr(self, "purchase_receipt", None),
			getattr(self, "purchase_invoice", None),
			has_update_stock,
		)
		if receipt is None:
			frappe.throw(
				"Recosting needs a Purchase Receipt or an exterior invoice with Update Stock checked."
			)
		try:
			taxes = build_lcv_taxes(self._lcv_leg("freight_invoice"), self._lcv_leg("insurance_invoice"))
		except ValueError as exc:
			frappe.throw(str(exc))
		raise
		lcv = frappe.get_doc(
			{
				"doctype": "Landed Cost Voucher",
				"company": self.company,
				"posting_date": frappe.utils.today(),
				"distribute_charges_based_on": "Amount",
				"purchase_receipts": [{"receipt_document_type": receipt[0], "receipt_document": receipt[1]}],
				"taxes": taxes,
			}
		)
		lcv.get_items_from_purchase_receipts()
		lcv.insert(ignore_permissions=True)
		lcv.submit()
		frappe.db.set_value(self.doctype, self.name, "landed_cost_voucher", lcv.name)
		self.landed_cost_voucher = lcv.name
		return lcv.name

	def _lcv_leg(self, field: str) -> dict | None:
		"""Shape one linked cost invoice into an LCV tax leg (bench only)."""
		name = getattr(self, field, None)
		if not name:
			return None
		values = frappe.db.get_value("Purchase Invoice", name, ["net_total", "currency", "conversion_rate"])
		if values is None:  # pragma: no cover - existence proven upstream
			frappe.throw(f"Purchase Invoice '{name}' linked as {field} does not exist.")
		net_total, currency, conversion_rate = values
		expense_account = frappe.db.get_value(
			"Purchase Invoice Item", {"parent": name}, "expense_account", order_by="idx"
		)
		return {
			"source": name,
			"amount": float(net_total or 0.0),
			"expense_account": expense_account,
			"account_currency": currency or "USD",
			"exchange_rate": float(conversion_rate or 1.0),
		}

	def _gather_costs(self) -> dict:
		"""Accumulate FOB/freight/insurance from linked documents (bench only).

		FOB prefers the exterior invoice ``net_total`` (taxes excluded),
		then the receipt, then the order. All legs must share one currency;
		a mixed-currency settlement fails loud instead of converting silently.
		"""
		legs: dict[str, float] = {}
		currencies = set()
		for field in ("purchase_invoice", "purchase_receipt", "purchase_order"):
			name = getattr(self, field, None)
			if name and "fob" not in legs:
				fob, currency = self._leg_net_total(field, name)
				legs["fob"] = fob
				currencies.add(currency)
		for field, leg in (("freight_invoice", "freight"), ("insurance_invoice", "insurance")):
			name = getattr(self, field, None)
			if name:
				amount, currency = self._leg_net_total(field, name)
				legs[leg] = amount
				currencies.add(currency)
		if len(currencies) > 1:
			frappe.throw(f"Settlement legs mix currencies: {sorted(currencies)}. Use one currency.")
		return legs

	def _leg_net_total(self, field: str, name: str) -> tuple:
		values = frappe.db.get_value(LINK_DOCTYPES[field], name, ["net_total", "currency"])
		if values is None:  # pragma: no cover - existence proven upstream
			frappe.throw(f"{LINK_DOCTYPES[field]} '{name}' linked as {field} does not exist.")
		net_total, currency = values
		return float(net_total or 0.0), currency

	def _validate_linked_documents(self, links: dict) -> None:
		"""Database checks: existence, same company, not cancelled."""
		for role, ref in links.items():
			if not ref:
				continue
			doctype, name = ref
			values = frappe.db.get_value(doctype, name, ["company", "docstatus"])
			if values is None:
				frappe.throw(f"{doctype} '{name}' linked as {role} does not exist.")
			company, docstatus = values
			if company != self.company:
				frappe.throw(f"{doctype} '{name}' belongs to '{company}', not '{self.company}'.")
			if docstatus == 2:
				frappe.throw(f"{doctype} '{name}' linked as {role} is cancelled.")
