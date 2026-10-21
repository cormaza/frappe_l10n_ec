import compileall
import importlib
import importlib.metadata
import inspect
import json
import unittest
from pathlib import Path

import l10n_ec
from l10n_ec import hooks

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

APP_ROOT = Path(l10n_ec.__file__).resolve().parent


def _to_snake_case(title: str) -> str:
	return title.strip().lower().replace(" ", "_")


def _to_pascal_case(doctype_name: str) -> str:
	return "".join(part for part in doctype_name.strip().split())


class TestAppInstallability(UnitTestCase):
	"""Verify Frappe v16 app structure, hooks, DocType schemas, and unittest runner compatibility."""

	def test_python_bytecode_compilation(self) -> None:
		"""Verify that all Python modules in l10n_ec compile without syntax errors on Python 3.14."""
		self.assertTrue(compileall.compile_dir(str(APP_ROOT), force=True, quiet=1))

	def test_package_metadata_and_hooks(self) -> None:
		"""Verify Frappe v16 app hooks and package distribution metadata."""
		self.assertTrue(
			l10n_ec.__version__.startswith("16."),
			f"Expected Frappe v16 major version '16.x.y', got '{l10n_ec.__version__}'",
		)
		self.assertEqual(importlib.metadata.version("l10n_ec"), l10n_ec.__version__)
		self.assertEqual(hooks.app_name, "l10n_ec")
		self.assertEqual(hooks.app_title, "Ecuador Localization")
		self.assertIn("frappe", hooks.required_apps)
		self.assertIn("erpnext", hooks.required_apps)

	def test_modules_and_patches_files(self) -> None:
		"""Verify modules.txt and patches.txt exist and each module has a valid Python package."""
		modules_file = APP_ROOT / "modules.txt"
		patches_file = APP_ROOT / "patches.txt"
		self.assertTrue(modules_file.is_file())
		self.assertTrue(patches_file.is_file())

		modules = [
			line.strip() for line in modules_file.read_text(encoding="utf-8").splitlines() if line.strip()
		]
		self.assertIn("Ecuador Localization", modules)
		for module_title in modules:
			module_pkg = APP_ROOT / _to_snake_case(module_title)
			self.assertTrue(module_pkg.is_dir(), f"Missing module directory for {module_title}")
			self.assertTrue((module_pkg / "__init__.py").is_file())

	def test_doctypes_schema_and_controllers(self) -> None:
		"""Verify every DocType JSON schema, field_order integrity, and controller class import."""
		modules_file = APP_ROOT / "modules.txt"
		declared_modules = {
			line.strip() for line in modules_file.read_text(encoding="utf-8").splitlines() if line.strip()
		}

		doctype_jsons = list(APP_ROOT.glob("*/doctype/*/*.json"))
		self.assertGreaterEqual(len(doctype_jsons), 1)

		for json_path in doctype_jsons:
			data = json.loads(json_path.read_text(encoding="utf-8"))
			self.assertEqual(data.get("doctype"), "DocType")
			self.assertIn(data.get("module"), declared_modules)
			doctype_name = data["name"]

			field_names = [f["fieldname"] for f in data.get("fields", [])]
			self.assertEqual(data.get("field_order"), field_names)
			self.assertGreaterEqual(len(data.get("permissions", [])), 1)

			controller_module_name = (
				f"l10n_ec.{_to_snake_case(data['module'])}.doctype.{json_path.parent.name}.{json_path.stem}"
			)
			controller_module = importlib.import_module(controller_module_name)
			expected_class_name = _to_pascal_case(doctype_name)
			self.assertTrue(
				hasattr(controller_module, expected_class_name),
				f"Controller {controller_module_name} missing class {expected_class_name}",
			)

	def test_fixture_records_carry_names(self) -> None:
		for path in sorted((APP_ROOT / "fixtures").glob("*.json")):
			rows = json.loads(path.read_text(encoding="utf-8"))
			for row in rows if isinstance(rows, list) else [rows]:
				self.assertIn("name", row, f"Fixture {path.name} record lacks 'name'")
		for path in sorted((APP_ROOT / "ecuador_localization" / "report").glob("*/*.json")):
			row = json.loads(path.read_text(encoding="utf-8"))
			self.assertIn("name", row, f"Report {path.name} lacks 'name'")

	def test_frappe_test_runner_discovery_compliance(self) -> None:
		"""Ensure all test_*.py modules use UnitTestCase/IntegrationTestCase classes and no bare test_ functions."""
		test_files = sorted(APP_ROOT.rglob("test_*.py"))
		self.assertGreaterEqual(len(test_files), 3)

		loader = unittest.TestLoader()
		for test_path in test_files:
			if test_path.name == "test_helpers.py":
				continue
			rel_parts = test_path.relative_to(APP_ROOT.parent).with_suffix("").parts
			module_name = ".".join(rel_parts)
			mod = importlib.import_module(module_name)

			bare_test_funcs = [
				name
				for name, obj in inspect.getmembers(mod, inspect.isfunction)
				if name.startswith("test_") and obj.__module__ == module_name
			]
			self.assertEqual(
				bare_test_funcs,
				[],
				f"{module_name} contains bare test_ functions ignored by Frappe bench run-tests: {bare_test_funcs}",
			)

			suite = loader.loadTestsFromModule(mod)
			self.assertGreater(
				suite.countTestCases(),
				0,
				f"{module_name} defines zero unittest.TestCase tests discoverable by Frappe bench run-tests",
			)
