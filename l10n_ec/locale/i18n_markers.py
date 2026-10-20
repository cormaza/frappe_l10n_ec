"""Gettext extraction markers for custom field labels and options.

`create_custom_fields` stores these strings in English in the database and
Frappe translates them at display time, so the definitions in
`custom_fields.py` intentionally stay raw. The bench pot scanner only
collects `_()` call literals, which is why every string below is repeated
here: this module exists for extraction and is never imported at runtime.
"""


def _(message: str) -> str:
	return message


CUSTOM_FIELD_STRINGS = [
	_("SRI Environment"),
	_("Test"),
	_("Production"),
	_("SRI Signature"),
	_("Special Taxpayer Resolution"),
	_("Withholding Agent Resolution"),
	_("RIMPE Regime"),
	_("Popular Business"),
	_("Entrepreneur"),
	_("Accounting Required"),
	_("SRI Identification Type"),
	_("Related Party"),
]
