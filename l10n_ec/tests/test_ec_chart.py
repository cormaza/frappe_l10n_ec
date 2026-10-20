import json
import unittest
from pathlib import Path

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

CHART_PATH = (
	Path(__file__).resolve().parent.parent
	/ "ecuador_localization"
	/ "chart_of_accounts"
	/ "ec_niif_chart_template.json"
)

METADATA_KEYS = {"account_number", "root_type", "account_type"}
ROOT_TYPES = {"Asset", "Liability", "Equity", "Income", "Expense"}

# Operational leaves appended by l10n_ec (not in the official SCVS chart):
# account_number -> tuple of ancestor names from the tree root.
OPERATIONAL_LEAVES = {
	"1010101": ("ACTIVO", "ACTIVO CORRIENTE", "EFECTIVO Y EQUIVALENTES AL EFECTIVO"),
	"1010102": ("ACTIVO", "ACTIVO CORRIENTE", "EFECTIVO Y EQUIVALENTES AL EFECTIVO"),
	"1010504": ("ACTIVO", "ACTIVO CORRIENTE", "ACTIVOS POR IMPUESTOS CORRIENTES"),
	"1010505": ("ACTIVO", "ACTIVO CORRIENTE", "ACTIVOS POR IMPUESTOS CORRIENTES"),
	"2010707": ("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES"),
	"2010708": ("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES"),
	"2010709": ("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES"),
	"2010710": ("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES"),
	"2010711": ("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES"),
}


def _walk(node, path=()):
	for name, child in node.items():
		if name in METADATA_KEYS:
			continue
		yield (*path, name), child
		yield from _walk(child, (*path, name))


class TestEcuadorChart(UnitTestCase):
	"""Structural tests for the Ecuador NIIF chart template (no database)."""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		doc = json.loads(CHART_PATH.read_text(encoding="utf-8"))
		cls.tree = doc["tree"]
		cls.nodes = dict(_walk(cls.tree))
		cls.numbers = {
			child["account_number"]: path for path, child in cls.nodes.items() if "account_number" in child
		}

	def test_chart_envelope(self) -> None:
		doc = json.loads(CHART_PATH.read_text(encoding="utf-8"))
		self.assertEqual(doc["country_code"], "ec")
		self.assertTrue(doc["name"])
		self.assertGreater(len(self.nodes), 300)

	def test_every_node_has_an_account_number(self) -> None:
		missing = [path for path, child in self.nodes.items() if "account_number" not in child]
		self.assertEqual(missing, [])

	def test_root_types_only_on_roots_and_valid(self) -> None:
		for name, child in self.tree.items():
			self.assertIn(child.get("root_type"), ROOT_TYPES, f"Root '{name}'")
		nested_with_root = [
			path for path, child in self.nodes.items() if len(path) > 1 and "root_type" in child
		]
		self.assertEqual(nested_with_root, [])

	def test_account_numbers_are_unique(self) -> None:
		seen = {}
		dupes = set()
		for path, child in self.nodes.items():
			number = child.get("account_number")
			if number in seen:
				dupes.add(number)
			seen[number] = path
		self.assertEqual(dupes, set())

	def test_official_anchors_live_at_the_right_parents(self) -> None:
		self.assertEqual(
			self.numbers["10101"], ("ACTIVO", "ACTIVO CORRIENTE", "EFECTIVO Y EQUIVALENTES AL EFECTIVO")
		)
		self.assertEqual(
			self.numbers["2010701"],
			(
				"PASIVO",
				"PASIVO CORRIENTE",
				"OTRAS OBLIGACIONES CORRIENTES",
				"CON LA ADMINISTRACIÓN TRIBUTARIA",
			),
		)
		self.assertEqual(self.numbers["61"], ("15% PARTICIPACIÓN TRABAJADORES",))

	def test_computed_groups_are_excluded(self) -> None:
		numbers = set(self.numbers)
		for excluded in ("42", "60", "62", "64", "67", "79", "82", "95", "99"):
			self.assertNotIn(excluded, numbers)
		names = [path[-1] for path in self.nodes]
		self.assertNotIn("GANANCIA BRUTA --> Subtotal A (41 - 51)", names)
		self.assertFalse(any("ELIMINADO" in name for name in names))

	def test_operational_leaves(self) -> None:
		for number, ancestors in OPERATIONAL_LEAVES.items():
			self.assertIn(number, self.numbers, f"Missing operational leaf {number}")
			self.assertEqual(self.numbers[number][: len(ancestors)], ancestors)
		leaves = dict(_walk(self.tree))
		self.assertEqual(
			leaves[("ACTIVO", "ACTIVO CORRIENTE", "EFECTIVO Y EQUIVALENTES AL EFECTIVO", "CAJA")][
				"account_type"
			],
			"Cash",
		)
		self.assertEqual(
			leaves[("ACTIVO", "ACTIVO CORRIENTE", "EFECTIVO Y EQUIVALENTES AL EFECTIVO", "BANCOS")][
				"account_type"
			],
			"Bank",
		)
