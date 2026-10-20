# DocTypes

DocTypes are the core data model in Frappe. Each DocType becomes a database table and gets auto-generated CRUD APIs, forms, and list views.

## Creating a DocType

File paths depend on workspace mode:
- **Standalone App Repository Mode**: `<app>/<module>/doctype/<doctype_name>/` (e.g. `l10n_ec/ecuador_localization/doctype/sri_signature/`)
- **Full `frappe-bench` Mode**: `apps/<app>/<app>/<module>/doctype/<doctype_name>/`

Each DocType directory contains:
- `<doctype_name>.json` — DocType schema definition (`field_order` must list every `fieldname` in `fields` in exact order, and `module` must match an entry in `<app>/modules.txt`)
- `<doctype_name>.py` — Python controller class inheriting from `frappe.model.document.Document` (named in PascalCase, e.g. `SRISignature` for `"name": "SRI Signature"`)
- `test_<doctype_name>.py` — `UnitTestCase` / `IntegrationTestCase` test suite
- `__init__.py` — package marker

Minimal `<doctype_name>.json` example:
```json
{
 "actions": [],
 "autoname": "format:EXP-{####}",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "title",
  "amount",
  "status"
 ],
 "fields": [
  {
   "fieldname": "title",
   "fieldtype": "Data",
   "label": "Title",
   "reqd": 1
  },
  {
   "fieldname": "amount",
   "fieldtype": "Currency",
   "label": "Amount",
   "reqd": 1
  },
  {
   "default": "Draft",
   "fieldname": "status",
   "fieldtype": "Select",
   "label": "Status",
   "options": "Draft\nApproved\nRejected"
  }
 ],
 "is_submittable": 0,
 "links": [],
 "module": "Ecuador Localization",
 "name": "Expense",
 "naming_rule": "Expression",
 "permissions": [
  {
   "create": 1,
   "delete": 1,
   "read": 1,
   "role": "System Manager",
   "write": 1
  }
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

## Common field types

| fieldtype | Use for |
|-----------|---------|
| Data | Short text (140 chars) |
| Small Text | Multi-line text |
| Text Editor | Rich text (HTML) |
| Int / Float | Number |
| Currency | Money amounts |
| Date / Datetime | Date, or date with time |
| Select | Dropdown (options separated by `\n`) |
| Link | Foreign key to another DocType |
| Table | Child table (one-to-many) |
| Check | Boolean (0/1) |
| Attach | File attachment |
| Password | Encrypted secret / password |

## Naming patterns

- `autoname: "format:EXP-{####}"` — sequential (EXP-0001, EXP-0002)
- `autoname: "field:title"` — use field value as name
- `autoname: "hash"` — random hash
- `autoname: "naming_series:"` — user-configurable series
- `autoname: "prompt"` — user enters name manually

## Child DocTypes

For one-to-many relationships (e.g. Expense Items inside an Expense):

1. Create a child DocType JSON with `"istable": 1`
2. Add a `Table` field in the parent pointing to it:
```json
{
    "fieldname": "items",
    "fieldtype": "Table",
    "label": "Items",
    "options": "Expense Item"
}
```

A child DocType needs no permissions. It inherits them from the parent.

## Validating DocTypes

- **In Standalone App Repository Mode (Ring 1)**:
  ```bash
  .venv/bin/pytest -v -W error
  ```
  `TestAppInstallability::test_doctypes_schema_and_controllers` validates every `doctype/*/*.json` schema, `field_order` consistency, `modules.txt` membership, and controller class import.
- **In Full `frappe-bench` Mode (Ring 2)**:
  ```bash
  bench --site <site> migrate
  ```

## Other useful JSON keys

```json
{
    "sort_field": "modified",
    "sort_order": "DESC",
    "track_changes": 1,
    "is_submittable": 1
}
```

Submittable DocTypes get a `docstatus` field automatically: `0` = Draft, `1` = Submitted, `2` = Cancelled. Users cannot edit submitted documents — they must cancel and amend.

Do NOT add `creation`, `modified`, `owner`, `modified_by`, or `docstatus` as fields in `fields` — Frappe manages these columns automatically.
