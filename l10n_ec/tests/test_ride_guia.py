import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.voucher_mail import build_attachments, ride_print_format

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sri_ride_guia_print_format.json"


def _load_ride() -> dict:
	"""Load the guia RIDE fixture record."""
	return json.loads(FIXTURE.read_text(encoding="utf-8"))[0]


class TestRideGuiaPrintFormat(UnitTestCase):
	"""Unit tests for the guia de remision (06) RIDE print format."""

	def test_fixture_has_explicit_name(self) -> None:
		ride = _load_ride()
		self.assertEqual(ride["name"], "SRI RIDE Delivery Note")
		self.assertEqual(ride["doctype"], "Print Format")

	def test_fixture_targets_delivery_note_with_weasyprint(self) -> None:
		ride = _load_ride()
		self.assertEqual(ride["doc_type"], "Delivery Note")
		self.assertEqual(ride["print_format_type"], "Jinja")
		self.assertEqual(ride["pdf_generator"], "WeasyPrint")
		self.assertEqual(ride["disabled"], 0)

	def test_html_renders_transport_blocks_and_lines(self) -> None:
		html = _load_ride()["html"]
		for token in (
			"sri_voucher_data(",
			"Delivery Note",
			"sri_emisor(doc.company)",
			"sri_barcode(voucher.access_key)",
			"voucher.access_key",
			"Origin Address:",
			"Carrier:",
			"Transport Dates:",
			"Plate:",
			"Recipient",
			"Transfer Reason:",
			"Support Document:",
			"for recipient in body.recipients",
			"for row in recipient.lines",
			"DOCUMENT IN PROCESS",
		):
			with self.subTest(token=token):
				self.assertIn(token, html)

	def test_ride_format_mapping_for_guia(self) -> None:
		self.assertEqual(ride_print_format("06"), "SRI RIDE Delivery Note")

	def test_build_attachments_pairs_xml_with_guia_ride(self) -> None:
		attachments = build_attachments("fid-6", "06", "Delivery Note", "DN-1")
		self.assertEqual(len(attachments), 2)
		self.assertEqual(attachments[1]["print_format"], "SRI RIDE Delivery Note")

	def test_unknown_code_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			build_attachments("fid-6", "99", "Delivery Note", "DN-1")

	def test_jinja_helpers_registered_in_hooks(self) -> None:
		text = (Path(__file__).resolve().parent.parent / "hooks.py").read_text(encoding="utf-8")
		for helper in ("sri_barcode", "sri_authorized_voucher", "sri_voucher_data", "sri_emisor"):
			with self.subTest(helper=helper):
				self.assertIn(f"l10n_ec.ecuador_localization.jinja.{helper}", text)
