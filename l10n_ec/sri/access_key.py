import re
import unicodedata
from datetime import date
from random import randint

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


def clean_sri_string(str_to_clean: str) -> str:
	"""Strip accents and characters outside SRI's allowed XML character set.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_document.py::_l10n_ec_clean_str`).
	"""
	nfkd_form = unicodedata.normalize("NFKD", str_to_clean or "")
	without_accents = "".join(c for c in nfkd_form if not unicodedata.combining(c))
	return re.sub(r"[^-A-Za-z0-9/?:().,'+ ]", "", without_accents)


def split_document_number(document_number: str) -> tuple[str, str, str]:
	"""Split an Ecuadorian document number `001-001-012345678` into zero-padded parts.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_document.py::_l10n_ec_split_document_number`).
	"""
	parts = document_number.split("-")
	if len(parts) != 3:
		raise ValueError(
			_("Invalid Ecuadorian document number '{}'. Expected format '001-001-000000001'.").format(
				document_number
			)
		)
	entity_number, printer_point, sequence_number = parts
	return (
		entity_number.rjust(3, "0"),
		printer_point.rjust(3, "0"),
		sequence_number.rjust(9, "0"),
	)


def compute_mod11_check_digit(access_key_48: str) -> int:
	"""Compute the SRI Modulo 11 check digit for a 48-digit access key payload.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_document.py::l10n_ec_get_check_digit`).
	According to SRI Electronic Invoicing Technical Sheet (Table 1).
	"""
	if len(access_key_48) != 48 or not access_key_48.isdigit():
		raise ValueError(_("Access key payload must be exactly 48 numeric digits before check digit."))

	mult = 1
	current_sum = 0
	for i in reversed(range(len(access_key_48))):
		mult += 1
		if mult == 8:
			mult = 2
		current_sum += int(access_key_48[i]) * mult

	check_digit = 11 - (current_sum % 11)
	if check_digit == 11:
		check_digit = 0
	elif check_digit == 10:
		check_digit = 1
	return check_digit


def generate_access_key(
	document_code_sri: str,
	complete_document_number: str,
	environment: str,
	date_document: date,
	ruc: str,
	numeric_code: str | int | None = None,
	emission_type: str = "1",
) -> str:
	"""Generate a 49-digit SRI Access Key (`claveAcceso`) according to SRI Table 1.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_document.py::l10n_ec_generate_access_key`).
	:param document_code_sri: 2-digit SRI voucher type code (e.g. '01' for Invoice, '04' Credit Note).
	:param complete_document_number: 15-digit concatenated number (estab + ptoEmi + secuencial) or '001-001-000000001'.
	:param environment: '1' for Test (Pruebas), '2' for Production (Produccion).
	:param date_document: Document emission date.
	:param ruc: 13-digit Ecuadorian taxpayer RUC.
	:param numeric_code: Optional 8-digit random numeric code (generated if omitted).
	:param emission_type: '1' for normal emission (SRI standard).
	"""
	if "-" in complete_document_number:
		estab, pto_emi, seq = split_document_number(complete_document_number)
		complete_document_number = f"{estab}{pto_emi}{seq}"

	if len(complete_document_number) != 15 or not complete_document_number.isdigit():
		raise ValueError(
			_("Complete document number must be 15 digits (got '{}').").format(complete_document_number)
		)
	if len(ruc) != 13 or not ruc.isdigit():
		raise ValueError(_("Company RUC must be 13 numeric digits (got '{}').").format(ruc))
	if environment not in ("1", "2"):
		raise ValueError(
			_("SRI environment must be '1' (test) or '2' (production), got '{}'.").format(environment)
		)
	if len(document_code_sri) != 2 or not document_code_sri.isdigit():
		raise ValueError(_("Document SRI code must be 2 digits (got '{}').").format(document_code_sri))

	now_date = date_document.strftime("%d%m%Y")
	if numeric_code is None:
		numeric_code_str = str(randint(1, 99999999)).rjust(8, "0")
	else:
		numeric_code_str = str(numeric_code).rjust(8, "0")

	if len(numeric_code_str) != 8 or not numeric_code_str.isdigit():
		raise ValueError(_("Numeric code must be 8 digits (got '{}').").format(numeric_code_str))

	access_key_48 = (
		now_date
		+ document_code_sri
		+ ruc
		+ environment
		+ complete_document_number
		+ numeric_code_str
		+ emission_type
	)
	check_digit = compute_mod11_check_digit(access_key_48)
	return f"{access_key_48}{check_digit}"
