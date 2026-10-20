import unittest

from l10n_ec.ecuador_localization.doctype.sri_emission_point.sri_emission_point import (
	SRIEmissionPoint,
)
from l10n_ec.ecuador_localization.doctype.sri_emission_sequence.sri_emission_sequence import (
	SRIEmissionSequence,
)

try:
	import frappe
	from frappe.tests import UnitTestCase

	EXPECTED_ERROR = (ValueError, frappe.ValidationError)
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]
	EXPECTED_ERROR = ValueError


def _row(document_type=None, current_sequence=0):
	if frappe is not None:
		return {"document_type": document_type, "current_sequence": current_sequence}
	return SRIEmissionSequence(document_type=document_type, current_sequence=current_sequence)


def _point(**kwargs):
	values = {"establishment_code": "001", "emission_point_code": "001"}
	values.update(kwargs)
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Emission Point", **values})
	return SRIEmissionPoint(**values)


class TestSRIEmissionPoint(UnitTestCase):
	"""Unit tests for the SRI Emission Point controller (in-memory, no database)."""

	def test_valid_codes_pass_validation(self) -> None:
		doc = _point(
			sequences=[_row("01", 41)],
		)
		doc.validate()
		self.assertEqual(doc.establishment_code, "001")

	def test_non_digit_codes_are_rejected(self) -> None:
		with self.assertRaises(EXPECTED_ERROR):
			_point(establishment_code="0A1").validate()
		with self.assertRaises(EXPECTED_ERROR):
			_point(emission_point_code="01").validate()
		with self.assertRaises(EXPECTED_ERROR):
			_point(establishment_code="0001").validate()

	def test_sequence_row_requires_document_type(self) -> None:
		doc = _point(sequences=[_row(None, 1)])
		with self.assertRaises(EXPECTED_ERROR):
			doc.validate()

	def test_sequence_out_of_range_is_rejected(self) -> None:
		with self.assertRaises(EXPECTED_ERROR):
			_point(sequences=[_row("01", 1000000000)]).validate()
		with self.assertRaises(EXPECTED_ERROR):
			_point(sequences=[_row("01", -1)]).validate()
