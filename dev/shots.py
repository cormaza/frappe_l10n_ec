"""Demo screenshot capture for docs/wiki (Spanish desk, tight framing).

Prerequisites: infra up and desk serving with a seeded Spanish demo::

	dev/demo.sh up
	dev/demo.sh reset     # site + seed + Administrator language=es + es.mo
	dev/demo.sh serve     # http://demo:8000 (add 127.0.0.1 demo to /etc/hosts)

Then::

	.venv/bin/python dev/shots.py [--only 01,10] [--out docs/wiki/img]

Documents are resolved through the REST API (company, sustento, doc code)
so a reseed never breaks the shot list. Dialogs are captured as modal
elements; long forms as viewport shots scrolled to their section.

Requires playwright + pillow in the local .venv only (never in
pyproject dev deps: CI never runs this script).
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://demo:8000"
USER = "Administrator"
PASSWORD = "admin"
VIEWPORT = {"width": 1366, "height": 900}
OUT_DIR = Path("docs/wiki/img")
CHROME = "/home/christopher/.local/bin/google-chrome"


def api_get(page, doctype, fields, filters=None, limit=20, order_by=None):
	params = [
		("fields", "[%s]" % ",".join('"%s"' % f for f in fields)),
		("limit_page_length", str(limit)),
	]
	if filters:
		params.append(("filters", json.dumps(filters)))
	if order_by:
		params.append(("order_by", order_by))
	query = "&".join("%s=%s" % (k, quote(v)) for k, v in params)
	resp = page.request.get("%s/api/resource/%s?%s" % (BASE, quote(doctype), query))
	if not resp.ok:
		raise RuntimeError("GET %s -> %s %s" % (doctype, resp.status, resp.text()))
	return resp.json()["data"]


def first(rows):
	assert rows, "no rows returned by the demo API; is the site seeded?"
	return rows[0]["name"]


def goto_ready(page, url):
	page.goto(url, wait_until="domcontentloaded", timeout=90000)
	page.wait_for_selector(".page-container", timeout=90000)
	time.sleep(2)


def set_report_filters(page, company, year, month):
	page.wait_for_selector('[data-fieldname="company"]', timeout=60000)
	time.sleep(1)
	page.evaluate(
		"frappe.query_report.set_filter_value({company: %s, year: %s, month: %s})"
		% (json.dumps(company), int(year), int(month))
	)
	page.wait_for_function("frappe.query_report.data && frappe.query_report.data.length > 0", timeout=60000)
	time.sleep(2)


def ensure_section_open(page, text):
	"""Expand a collapsible form section if it rendered collapsed (no-op otherwise)."""
	head = page.locator(".section-head", has_text=text).first
	try:
		if head.count() and "collapsed" in (head.get_attribute("class") or ""):
			head.click()
			time.sleep(1)
	except Exception:
		pass


def scroll_to_text(page, text):
	matches = page.get_by_text(text, exact=False)
	for index in range(min(matches.count(), 10)):
		if matches.nth(index).is_visible():
			matches.nth(index).scroll_into_view_if_needed()
			time.sleep(1)
			return
	raise RuntimeError("no visible match for %r on %s" % (text, page.url))


def shot(page, name, out):
	page.keyboard.press("Escape")
	time.sleep(1)
	page.screenshot(path=str(out / name))
	size = Image.open(out / name).size
	print("%s %sx%s" % (name, size[0], size[1]))


def capture_modal(page, button_text, name, out):
	page.get_by_role("button", name=button_text).first.click()
	modal = page.locator(".modal.show .modal-content")
	modal.wait_for(timeout=30000)
	time.sleep(1)
	page.keyboard.press("Tab")
	time.sleep(1)
	modal.screenshot(path=str(out / name))
	print("%s (modal)" % name)


MODAL_SHOTS = frozenset({"13-pi-import-dialog.png", "14-pi-fetch-dialog.png", "16-rw-import-dialog.png"})


def run(selected, out):
	plan = []

	def add(key, filename, fn):
		if not selected or key in selected:
			plan.append((filename, fn))

	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True, executable_path=CHROME)
		page = browser.new_page(viewport=VIEWPORT)
		login = page.request.post("%s/api/method/login" % BASE, data={"usr": USER, "pwd": PASSWORD})
		assert login.ok, "login failed: %s" % login.text()

		pinv = lambda **kw: first(  # noqa: E731
			api_get(
				page,
				"Purchase Invoice",
				["name"],
				[["company", "=", "Demo Ecuador"], ["docstatus", "=", 1]]
				+ [[k, "=", v] for k, v in kw.items()],
			)
		)
		sinv_rows = api_get(
			page,
			"Sales Invoice",
			["name", "sri_ir_concepto"],
			[["company", "=", "Demo Ecuador"], ["docstatus", "=", 1]],
			limit=10,
			order_by="creation asc",
		)
		sinv = next((row["name"] for row in sinv_rows if row.get("sri_ir_concepto")), first(sinv_rows))
		voucher01 = first(
			api_get(
				page,
				"SRI Electronic Voucher",
				["name"],
				[["sri_doc_code", "=", "01"]],
			)
		)
		voucher_rows = api_get(
			page,
			"SRI Electronic Voucher",
			["name", "sri_exterior_regime"],
			[["sri_doc_code", "=", "07"]],
			limit=10,
			order_by="creation desc",
		)
		voucher07 = next(
			(row["name"] for row in voucher_rows if row.get("sri_exterior_regime") == "paraiso"),
			first(voucher_rows),
		)
		settlement = first(api_get(page, "SRI Import Settlement", ["name"]))
		lcv = first(api_get(page, "Landed Cost Voucher", ["name"]))
		mandante = pinv(sri_is_reimbursement=1)
		intermediario = first(
			api_get(
				page,
				"Purchase Invoice",
				["name"],
				[
					["company", "=", "Demo Ecuador"],
					["docstatus", "=", 1],
					["sri_sustento_code", "like", "08%"],
				],
			)
		)
		exterior_rows = api_get(
			page,
			"Purchase Invoice",
			["name", "bill_no"],
			[["company", "=", "Demo Ecuador"], ["bill_no", "like", "990%"]],
			limit=10,
		)
		assert exterior_rows, "no exterior PINV seeded"
		exterior = max(exterior_rows, key=lambda row: row.get("bill_no") or "")["name"]
		probe_rows = api_get(
			page,
			"Purchase Invoice",
			["posting_date"],
			[["company", "=", "Demo Ecuador"], ["docstatus", "=", 1]],
			limit=1,
			order_by="creation desc",
		)
		assert probe_rows, "no submitted PINV to derive the report period"
		year, month = probe_rows[0]["posting_date"].split("-")[:2]
		month = str(int(month))

		add("01", "01-workspace.png", lambda: goto_ready(page, "%s/app/ecuador-localization" % BASE))
		add(
			"11",
			"11-workspace-reception.png",
			lambda: goto_ready(page, "%s/app/sri-import-settlement/view/list" % BASE),
		)
		add(
			"02",
			"02-pi-taxes.png",
			lambda: (
				goto_ready(page, "%s/app/purchase-invoice/%s" % (BASE, pinv())),
				scroll_to_text(page, "Desglose de impuestos"),
				ensure_section_open(page, "Desglose de impuestos"),
			),
		)
		add(
			"03",
			"03-assumed-flag.png",
			lambda: (
				goto_ready(page, "%s/app/purchase-invoice/%s" % (BASE, pinv())),
				scroll_to_text(page, "Factura de Proveedor"),
			),
		)
		add(
			"04",
			"04-si-facturacion-sri.png",
			lambda: (
				goto_ready(page, "%s/app/sales-invoice/%s" % (BASE, sinv)),
				scroll_to_text(page, "Facturación SRI"),
				ensure_section_open(page, "Facturación SRI"),
			),
		)
		add(
			"05",
			"05-voucher-list.png",
			lambda: goto_ready(page, "%s/app/sri-electronic-voucher/view/list" % BASE),
		)
		add(
			"06",
			"06-voucher-01.png",
			lambda: goto_ready(page, "%s/app/sri-electronic-voucher/%s" % (BASE, voucher01)),
		)
		add(
			"07",
			"07-voucher-07.png",
			lambda: goto_ready(page, "%s/app/sri-electronic-voucher/%s" % (BASE, voucher07)),
		)

		for key, filename, report in [
			("08", "08-form-104.png", "SRI Form 104"),
			("09", "09-form-103.png", "SRI Form 103"),
			("10", "10-ats.png", "SRI ATS"),
		]:

			def make_report(report=report):
				goto_ready(page, "%s/app/query-report/%s" % (BASE, quote(report)))
				set_report_filters(page, "Demo Ecuador", year, month)

			add(key, filename, make_report)

		add("12", "12-pi-import-buttons.png", lambda: goto_ready(page, "%s/app/purchase-invoice/new" % BASE))
		add(
			"13",
			"13-pi-import-dialog.png",
			lambda: (
				goto_ready(page, "%s/app/purchase-invoice/new" % BASE),
				capture_modal(page, "Importar XML del proveedor", "13-pi-import-dialog.png", out),
			),
		)
		add(
			"14",
			"14-pi-fetch-dialog.png",
			lambda: (
				goto_ready(page, "%s/app/purchase-invoice/new" % BASE),
				capture_modal(page, "Obtener XML del proveedor por clave", "14-pi-fetch-dialog.png", out),
			),
		)
		add(
			"15",
			"15-rw-new.png",
			lambda: goto_ready(page, "%s/app/sri-received-withholding/new" % BASE),
		)
		add(
			"16",
			"16-rw-import-dialog.png",
			lambda: (
				goto_ready(page, "%s/app/sri-received-withholding/new" % BASE),
				capture_modal(page, "Importar XML del cliente", "16-rw-import-dialog.png", out),
			),
		)
		add(
			"17",
			"17-settlement-goods.png",
			lambda: goto_ready(page, "%s/app/sri-import-settlement/%s" % (BASE, settlement)),
		)
		add(
			"18",
			"18-settlement-dai.png",
			lambda: (
				goto_ready(page, "%s/app/sri-import-settlement/%s" % (BASE, settlement)),
				scroll_to_text(page, "Valores declarados de la DAI"),
				ensure_section_open(page, "Valores declarados de la DAI"),
			),
		)
		add(
			"19",
			"19-settlement-totals.png",
			lambda: (
				goto_ready(page, "%s/app/sri-import-settlement/%s" % (BASE, settlement)),
				scroll_to_text(page, "Totales computados"),
				ensure_section_open(page, "Totales computados"),
			),
		)
		add(
			"20",
			"20-reimb-mandante.png",
			lambda: (
				goto_ready(page, "%s/app/purchase-invoice/%s" % (BASE, mandante)),
				scroll_to_text(page, "Detalles de reembolso SRI"),
				ensure_section_open(page, "Detalles de reembolso SRI"),
			),
		)
		add(
			"21",
			"21-reimb-intermediario.png",
			lambda: (
				goto_ready(page, "%s/app/purchase-invoice/%s" % (BASE, intermediario)),
				scroll_to_text(page, "Factura de Proveedor"),
			),
		)
		add(
			"22",
			"22-import-exterior-pi.png",
			lambda: goto_ready(page, "%s/app/purchase-invoice/%s" % (BASE, exterior)),
		)
		add(
			"23",
			"23-import-lcv.png",
			lambda: goto_ready(page, "%s/app/landed-cost-voucher/%s" % (BASE, lcv)),
		)

		for filename, fn in plan:
			fn()
			if filename not in MODAL_SHOTS:
				shot(page, filename, out)

		browser.close()


def main(argv):
	parser = argparse.ArgumentParser(description="Capture demo screenshots for docs/wiki.")
	parser.add_argument("--only", default="", help="Comma-separated shot keys, e.g. 01,10")
	parser.add_argument("--out", default=str(OUT_DIR), help="Output directory")
	args = parser.parse_args(argv)
	selected = {s for s in args.only.split(",") if s} if args.only else set()
	out = Path(args.out)
	out.mkdir(parents=True, exist_ok=True)
	run(selected, out)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
