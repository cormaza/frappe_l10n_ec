import json
import unittest
from pathlib import Path

from l10n_ec.ecuador_localization.voucher_mail import build_attachments, ride_print_format

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

FIXTURE = Path(__file__).resolve().parent.parent / 'fixtures' / 'sri_ride_retencion_print_format.json'


def _load_ride() -> dict:
	'''Load the retencion RIDE fixture record.'''
	return json.loads(FIXTURE.read_text(encoding='utf-8'))[0]


class TestRideRetencionPrintFormat(UnitTestCase):
	'''Unit tests for the comprobante de retencion (07) RIDE print format.'''

	def test_fixture_has_explicit_name(self) -> None:
		ride = _load_ride()
		self.assertEqual(ride['name'], 'SRI RIDE Withholding')
		self.assertEqual(ride['doctype'], 'Print Format')

	def test_fixture_targets_purchase_invoice_with_weasyprint(self) -> None:
		ride = _load_ride()
		self.assertEqual(ride['doc_type'], 'Purchase Invoice')
		self.assertEqual(ride['print_format_type'], 'Jinja')
		self.assertEqual(ride['pdf_generator'], 'WeasyPrint')
		self.assertEqual(ride['disabled'], 0)

	def test_html_renders_subject_period_sustento_and_withholdings(self) -> None:
		html = _load_ride()['html']
		for token in (
			'sri_voucher_data(',
			'Purchase Invoice',
			'sri_emisor(doc.company)',
			'sri_barcode(voucher.access_key)',
			'voucher.access_key',
			'Subject:',
			'Fiscal Period:',
			'Support Document',
			'for sustento in body.docs',
			'for row in sustento.withholdings',
			'Total Withheld:',
			'DOCUMENT IN PROCESS',
		):
			with self.subTest(token=token):
				self.assertIn(token, html)

	def test_ride_format_mapping_for_retencion(self) -> None:
		self.assertEqual(ride_print_format('07'), 'SRI RIDE Withholding')

	def test_build_attachments_pairs_xml_with_retencion_ride(self) -> None:
		attachments = build_attachments('fid-7', '07', 'Purchase Invoice', 'PINV-1')
		self.assertEqual(len(attachments), 2)
		self.assertEqual(attachments[1]['print_format'], 'SRI RIDE Withholding')

	def test_unknown_code_fails_loud(self) -> None:
		with self.assertRaises(ValueError):
			build_attachments('fid-7', '99', 'Purchase Invoice', 'PINV-1')
