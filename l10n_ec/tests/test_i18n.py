"""Ring 1 guard: every msgid we ship carries a real Spanish translation.

`bench update-po-files` prunes msgids its scanner cannot see and `msgfmt`
skips fuzzy entries, so an untranslated-or-fuzzy msgid silently renders in
English at runtime. This test parses `locale/es.po` with the standard
library only and fails naming every offender, except the documented
core-owned allowlist below.
"""

import unittest
from pathlib import Path

import l10n_ec

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

APP_ROOT = Path(l10n_ec.__file__).resolve().parent

#: Core-owned strings: Frappe core ships their translations in its own
#: catalog, so ours must stay untranslated (mirrors the AGENTS.md contract).
CORE_OWNED_UNTRANSLATED = frozenset({"Accounts User"})


def _unquote(chunk: str) -> str:
	chunk = chunk.strip()
	assert chunk.startswith('"') and chunk.endswith('"'), f"bad po chunk: {chunk!r}"
	return chunk[1:-1]


def _parse_po_entries(text: str) -> list:
	"""Split .po text into (msgid, msgstr, fuzzy) triples; header excluded."""
	entries = []
	msgid, msgstr, fuzzy, section = None, None, False, None
	for line in text.splitlines():
		stripped = line.strip()
		if not stripped:
			if msgid:
				entries.append((msgid, msgstr or "", fuzzy))
			msgid, msgstr, fuzzy, section = None, None, False, None
		elif stripped.startswith("#"):
			if "fuzzy" in stripped:
				fuzzy = True
		elif stripped.startswith("msgid"):
			section = "id"
			msgid = _unquote(stripped[5:])
		elif stripped.startswith("msgstr"):
			section = "str"
			msgstr = _unquote(stripped[6:])
		elif stripped.startswith('"'):
			if section == "id":
				msgid += _unquote(stripped)
			elif section == "str":
				msgstr += _unquote(stripped)
	if msgid:
		entries.append((msgid, msgstr or "", fuzzy))
	return entries


class TestI18nCompleteness(UnitTestCase):
	"""Every owned msgid ships translated and effective (non-fuzzy)."""

	def test_every_owned_msgid_is_translated(self) -> None:
		po_path = APP_ROOT / "locale" / "es.po"
		entries = _parse_po_entries(po_path.read_text(encoding="utf-8"))
		self.assertGreater(len(entries), 700, "es.po looks truncated; refusing to pass vacuous")

		offenders = sorted(
			msgid
			for msgid, msgstr, fuzzy in entries
			if (not msgstr or fuzzy) and msgid not in CORE_OWNED_UNTRANSLATED
		)
		self.assertEqual(
			offenders,
			[],
			"untranslated or fuzzy msgids render in English at runtime: " + "; ".join(offenders[:10]),
		)
