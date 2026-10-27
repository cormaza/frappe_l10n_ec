"""SRI import settlement link set (pure Python, no frappe).

T2 scope: which source documents a settlement may reference. The goods
themselves arrive through a Purchase Order, a Purchase Receipt, or the
exterior Purchase Invoice (FOB); freight and insurance arrive through
their own Purchase Invoices. Database checks (existence, company,
docstatus) belong to the controller; this module owns the set shape.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


#: Roles that carry the imported goods (at least one required).
GOODS_ROLES = ("purchase_order", "purchase_receipt", "purchase_invoice")

#: Roles that carry a cost leg of the settlement.
COST_ROLES = ("freight_invoice", "insurance_invoice")

#: Owning DocType per link role.
LINK_DOCTYPES = {
	"purchase_order": "Purchase Order",
	"purchase_receipt": "Purchase Receipt",
	"purchase_invoice": "Purchase Invoice",
	"freight_invoice": "Purchase Invoice",
	"insurance_invoice": "Purchase Invoice",
}


def validate_settlement_links(company: str | None, links: dict) -> None:
	"""Fail loud when the settlement link set is incomplete or ambiguous.

	`links` maps each role in (:data:`GOODS_ROLES` + :data:`COST_ROLES`)
	to a ``(doctype, name)`` tuple or ``None``. Requires the settlement
	company and at least one goods source; rejects one document serving
	two roles (a freight invoice is never the goods invoice).
	"""
	if not (company or "").strip():
		raise ValueError(_("Import settlement requires a company."))
	links = links or {}
	if not any((links.get(role) or (None, None))[1] for role in GOODS_ROLES):
		raise ValueError(
			_("Import settlement needs a goods source: purchase order, receipt, or exterior invoice.")
		)
	seen: dict[tuple, str] = {}
	for role in (*GOODS_ROLES, *COST_ROLES):
		ref = links.get(role)
		if not ref or not ref[1]:
			continue
		key = (ref[0], str(ref[1]).strip())
		if key in seen:
			raise ValueError(
				_("Document '{}' cannot serve as both {} and {}.").format(key[1], seen[key], role)
			)
		seen[key] = role
