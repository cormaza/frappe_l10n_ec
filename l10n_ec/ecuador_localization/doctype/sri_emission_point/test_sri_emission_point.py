import unittest

from l10n_ec.ecuador_localization.doctype.sri_emission_point.sri_emission_point import (
	SRIEmissionPoint,
)
from l10n_ec.ecuador_localization.doctype.sri_emission_sequence.sri_emission_sequence import (
	SRIEmissionSequence,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _point(**kwargs) -> SRIEmissionPoint:
	values = {"establishment_code": "001", "emission_point_code": "001"}
	values.update(kwargs)
	return SRIEmissionPoint(**values)


class TestSRIEmissionPoint(UnitTestCase):
	"""Unit tests for the SRI Emission Point controller (in-memory, no database)."""

	def test_valid_codes_pass_validation(self) -> None:
		doc = _point(
			sequences=[SRIEmissionSequence(document_type="01", current_sequence=41)],
		)
		doc.validate()
		self.assertEqual(doc.establishment_code, "001")

	def test_non_digit_codes_are_rejected(self) -> None:
		with self.assertRaises(ValueError):
			_point(establishment_code="0A1").validate()
		with self.assertRaises(ValueError):
			_point(emission_point_code="01").validate()
		with self.assertRaises(ValueError):
			_point(establishment_code="0001").validate()

	def test_sequence_row_requires_document_type(self) -> None:
		doc = _point(sequences=[SRIEmissionSequence(document_type=None, current_sequence=1)])
		with self.assertRaises(ValueError):
			doc.validate()

	def test_sequence_out_of_range_is_rejected(self) -> None:
		with self.assertRaises(ValueError):
			_point(
				sequences=[SRIEmissionSequence(document_type="01", current_sequence=1000000000)]
			).validate()
		with self.assertRaises(ValueError):
			_point(sequences=[SRIEmissionSequence(document_type="01", current_sequence=-1)]).validate()
