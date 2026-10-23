import inspect
import unittest

from l10n_ec.ecuador_localization import voucher_flow
from l10n_ec.ecuador_localization.custom_fields import CUSTOM_FIELDS
from l10n_ec.ecuador_localization.voucher_flow import (
	build_voucher_payload,
	create_and_process,
	process_voucher,
)
from l10n_ec.sri.payment_methods import TABLA_24, resolve_payment_method
from l10n_ec.sri.voucher_states import SriVoucherError

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

EXPECTED = {
	"01": "Sin utilización del sistema financiero",
	"15": "Compensación de deudas",
	"16": "Tarjeta de débito",
	"17": "Dinero electrónico",
	"18": "Tarjeta prepago",
	"19": "Tarjeta de crédito",
	"20": "Otros con utilización del sistema financiero",
	"21": "Endoso de títulos",
}

EMITTER = {
	"environment": "1",
	"ruc": "1790016919001",
	"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
	"trade_name": "",
	"head_office_address": "Av. Amazonas y Naciones Unidas",
	"establishment": "001",
	"emission_point": "001",
	"branch_address": "Av. Amazonas y Naciones Unidas",
	"special_taxpayer": "",
	"accounting_required": True,
}

SEQUENCE = {
	"sequential": "000000001",
	"access_key": "2410202601179001691900110010010000000011234567815",
}


def _invoice(payments):
	return {
		"doctype": "Sales Invoice",
		"cod_doc": "01",
		"issue_date": "20/10/2026",
		"buyer_id_type": "07",
		"buyer_name": "CONSUMIDOR FINAL",
		"buyer_id": "9999999999999",
		"buyer_address": "",
		"subtotal": 100.00,
		"discount": 0.0,
		"tax_totals": [],
		"tip": 0.0,
		"total": 115.00,
		"payments": payments,
		"lines": [],
	}


class TestPaymentMethods(UnitTestCase):
	"""Unit tests for the official SRI Tabla 24 payment method table (pure Python)."""

	def test_catalog_covers_all_sourced_codes(self) -> None:
		self.assertEqual(TABLA_24, EXPECTED)
		self.assertEqual(len(TABLA_24), 8)

	def test_all_codes_resolve_with_correct_description(self) -> None:
		for code, description in EXPECTED.items():
			with self.subTest(code=code):
				self.assertEqual(resolve_payment_method(code), description)

	def test_unknown_code_raises(self) -> None:
		for bad in ("00", "02", "99", "", "99 "):
			with self.subTest(code=bad):
				with self.assertRaises(SriVoucherError):
					resolve_payment_method(bad)


class TestPaymentMethodPayload(UnitTestCase):
	"""Explicit payment codes travel end-to-end through the payload builder."""

	def test_build_factura_payload_carries_explicit_code(self) -> None:
		payload = build_voucher_payload(_invoice([{"method": "19", "amount": 115.00}]), EMITTER, SEQUENCE)
		self.assertEqual(payload["data"]["payments"], [{"method": "19", "amount": 115.00}])

	def test_build_factura_payload_defaults_are_caller_owned(self) -> None:
		payload = build_voucher_payload(_invoice([{"method": "01", "amount": 115.00}]), EMITTER, SEQUENCE)
		self.assertEqual(payload["data"]["payments"], [{"method": "01", "amount": 115.00}])


class TestPaymentMethodThreading(UnitTestCase):
	"""Every flow entry point accepts and validates an explicit payment method."""

	def test_signatures_carry_defaulted_payment_method(self) -> None:
		for fn in (
			create_and_process,
			process_voucher,
			voucher_flow._assemble_payload,
			voucher_flow._invoice_dict,
			voucher_flow._withholding_subject_and_docs,
		):
			with self.subTest(fn=fn.__name__):
				param = inspect.signature(fn).parameters["payment_method"]
				self.assertEqual(param.default, "01")

	def test_entry_points_reject_unknown_codes_without_frappe(self) -> None:
		with self.assertRaises(SriVoucherError):
			create_and_process("Sales Invoice", "TEST-001", payment_method="99")
		with self.assertRaises(SriVoucherError):
			process_voucher("TEST-001", payment_method="99")


class TestPaymentMethodCustomField(UnitTestCase):
	"""Mode of Payment carries the Tabla 24 mapping point for Phase 9A."""

	def test_sri_payment_code_field_structure(self) -> None:
		fields = {f["fieldname"]: f for f in CUSTOM_FIELDS["Mode of Payment"]}
		field = fields["sri_payment_code"]
		self.assertEqual(field["label"], "SRI Payment Code")
		self.assertEqual(field["fieldtype"], "Select")
		self.assertEqual(field["default"], "01 - Sin utilización del sistema financiero")
		self.assertEqual({opt.split(" - ", 1)[0] for opt in field["options"].split("\n")}, set(TABLA_24))
		self.assertIn("Phase 9A", field["description"])

	def test_select_covers_all_tabla_24_codes(self) -> None:
		field = next(f for f in CUSTOM_FIELDS["Mode of Payment"] if f["fieldname"] == "sri_payment_code")
		options = field["options"].split("\n")
		self.assertEqual({opt.split(" - ", 1)[0] for opt in options}, set(TABLA_24))
		for opt in options:
			self.assertIn(" - ", opt)
