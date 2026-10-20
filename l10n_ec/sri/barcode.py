"""Code128 barcode rendering for SRI access keys (pure Python, no frappe)."""

import base64
import io

from barcode import Code128
from barcode.writer import ImageWriter


def access_key_barcode_png(access_key: str) -> bytes:
	"""Render the 49-digit access key as a Code128 PNG image."""
	key = (access_key or "").strip()
	if len(key) != 49 or not key.isdigit():
		raise ValueError(f"SRI access key must be 49 numeric digits (got '{access_key}').")
	buffer = io.BytesIO()
	Code128(key, writer=ImageWriter()).write(buffer)
	return buffer.getvalue()


def access_key_barcode_data_uri(access_key: str) -> str:
	"""Render the access key as a data-URI PNG for `<img>` tags in print formats."""
	raw = access_key_barcode_png(access_key)
	return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
