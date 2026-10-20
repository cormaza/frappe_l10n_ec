# `l10n_ec` Product & Technical Roadmap (Frappe / ERPNext v16)

This document defines the phased roadmap for **Ecuadorian Localization (`l10n_ec`)** on **Frappe Framework v16** and **ERPNext v16** (`Python 3.14`).

---

## Why `l10n_ec` Must Be Self-Contained in Frappe v16

In Odoo 19.0, Ecuadorian localization is split across two layers:
1. **Odoo Core (`addons/l10n_ec` + `l10n_latam_base` + `l10n_latam_invoice_document`)**: Provides the Chart of Accounts, tax groups, RUC/Cédula validation (`stdnum.ec`), document types (`01`–`41`), payment methods, and emission points.
2. **OCA (`OCA/l10n-ecuador`, PRs #101–#109)**: Extends Odoo Core with XAdES-BES electronic invoicing (`l10n_ec_account_edi`), credit/debit notes (`l10n_ec_credit_note`), withholdings (`l10n_ec_withhold`), delivery notes (`l10n_ec_delivery_note`), and tax reports (`l10n_ec_ats`, `l10n_ec_104`, `l10n_ec_103`).

In **ERPNext v16**, by contrast:
- `erpnext/regional/` contains **zero** Ecuadorian modules (`india`, `italy`, `germany`, `france`, `saudi_arabia`, `united_states` only).
- `erpnext/accounts/doctype/account/chart_of_accounts/unverified/ec_ec_chart_template.json` is an unverified legacy skeleton lacking `root_type` assignments, NIIF account numbers, and Ecuadorian tax templates.

Therefore, `l10n_ec` for Frappe v16 combines **both** the base accounting/catalog layer (`odoo/addons/l10n_ec`) and the full SRI electronic invoicing & tax compliance suite (`OCA/l10n-ecuador` PRs #101–#109) into a single, cohesive Frappe v16 app following the architecture of [`resilient-tech/india-compliance`](https://github.com/resilient-tech/india-compliance) and [`alyf-de/erpnext_germany`](https://github.com/alyf-de/erpnext_germany).

---

## Phased Implementation Roadmap

### Phase 0: Repository Foundation & Cryptographic Core (Completed)
- **Source Equivalence**: Core cryptographic and SOAP transport subset of [`OCA/l10n-ecuador` PR #102](https://github.com/OCA/l10n-ecuador/pull/102).
- **Delivered Components**:
  - Pure Python SRI package ([`l10n_ec/sri/`](../l10n_ec/sri/)) with zero top-level `frappe` imports:
    - [`signer.py`](../l10n_ec/sri/signer.py): PKCS#12 decoding (`cryptography >= 42`), multi-certificate chain selection (`KeyUsage.digital_signature`), UTC-aware validity dates (`not_valid_before_utc` / `not_valid_after_utc`), and XAdES-BES RSA-SHA1 enveloped XML signing (`xmlsig` + `xades==0.2.4`) with `pyOpenSSL >= 24` bypass.
    - [`access_key.py`](../l10n_ec/sri/access_key.py): 49-digit `claveAcceso` generator with Modulo 11 check digit (`compute_mod11_check_digit`, `generate_access_key`) and XML string sanitizer (`clean_sri_string`).
    - [`soap_client.py`](../l10n_ec/sri/soap_client.py) & [`wsdl/`](../l10n_ec/sri/wsdl/): Offline/online `zeep` SOAP client for `RecepcionComprobantesOffline` and `AutorizacionComprobantesOffline`.
  - Frappe v16 DocType [`SRI Signature`](../l10n_ec/ecuador_localization/doctype/sri_signature/sri_signature.json) (`SRISignature`).
  - Two-Ring TDD & CI: sub-second `pytest` (`UnitTestCase`), `pre-commit` (`ruff` `v0.14.10` + `pre-commit-hooks` `v6.0.0`), local `act` execution, and manual `workflow_dispatch` CI.

---

### Phase 1: Taxpayer Identification Validation (Pure Python)
- **Source Equivalence**: `stdnum.ec` checks in `odoo/addons/l10n_ec` + identification subset of [`OCA/l10n-ecuador` PR #101 (`l10n_ec_base`)](https://github.com/OCA/l10n-ecuador/pull/101).
- **Planned Scope**:
  1. Add `python-stdnum>=1.20` dependency and implement `l10n_ec/sri/identification.py` with format/validity checks for `RUC` (`04`, via `stdnum.ec.ruc`), `Cédula` (`05`, via `stdnum.ec.ci`), `Pasaporte` (`06`), `Consumidor Final` (`07` — literal `9999999999999` format only), and `Identificación del Exterior` (`08`).
  2. Ring 1 `UnitTestCase` coverage for valid, invalid, and boundary inputs per identification type.
- **Exit Criteria**: `identification.py` has zero top-level `frappe` imports; Ring 1 suite green. The `Consumidor Final` USD 50.00 amount threshold is explicitly out of scope here — it is a billing business rule, see Phase 6.

---

### Phase 2: SRI Master Catalog DocTypes & Seed Data
- **Source Equivalence**: catalog subset of `odoo/addons/l10n_ec` + [`OCA/l10n-ecuador` PR #101 (`l10n_ec_base`)](https://github.com/OCA/l10n-ecuador/pull/101).
- **Planned Scope**:
  1. `SRI Identification Type` (`04`–`08`)
  2. `SRI Document Type` (`01` Invoice, `03` Purchase Liquidation, `04` Credit Note, `05` Debit Note, `06` Delivery Note, `07` Withholding, `41` Reimbursement)
  3. `SRI Payment Method` (`01` Without Financial System, `15` Compensation, `16` Debit Card, `17` Electronic Money, `18` Prepaid Card, `19` Credit Card, `20` Other with Financial System, `21` Endorsement of Titles)
  4. `SRI Tax Support` (`Sustento Tributario` codes `01`–`15` for purchases and ATS)
  5. `SRI Emission Point` (`Establecimiento` 3-digit + `Punto de Emisión` 3-digit + per-document-type 9-digit sequences)
  6. Seed data via fixtures matching official SRI codes.
- **Exit Criteria**: all five DocTypes install cleanly on a test site; stored codes match the SRI specification exactly; controllers delegate format checks to `l10n_ec/sri/identification.py` (Phase 1).

---

### Phase 3: ERPNext Custom Fields & Install Wiring
- **Source Equivalence**: field customizations in `odoo/addons/l10n_ec` + [`OCA/l10n-ecuador` PR #101](https://github.com/OCA/l10n-ecuador/pull/101).
- **Planned Scope**:
  1. Wire `after_install` / `after_migrate` in `hooks.py` to idempotent `create_custom_fields`:
     - `Company`: `sri_environment` (`Test` / `Production`), `sri_signature` (`Link: SRI Signature`), `special_taxpayer_resolution`, `withholding_agent_resolution`, `rimpe_regime`, `accounting_required`.
     - `Customer` & `Supplier`: `sri_identification_type`, `sri_related_party` (`Parte Relacionada`).
- **Exit Criteria**: fresh install and re-migrate both apply fields without duplicates or errors; uninstall path removes the customizations.

---

### Phase 4: Ecuador NIIF Chart of Accounts & Tax Templates
- **Source Equivalence**: chart and tax definitions in `odoo/addons/l10n_ec` (replacing the unverified ERPNext `ec_ec_chart_template.json` skeleton).
- **Planned Scope**:
  1. Verified NIIF Chart of Accounts (`Superintendencia de Compañías`) with correct `root_type` assignments and NIIF account numbers.
  2. Tax templates: VAT 15%, VAT 5% (construction), VAT 0%, VAT Exempt, No Object of VAT, ICE, IRBPNR, Income & VAT Withholding rates.
- **Exit Criteria**: chart installs on a new Ecuadorian company; trial balance roots balance; every template posts to its intended account in a smoke test.

---

### Phase 5: Spanish Gettext Catalog (`es`)
- **Source Equivalence**: Frappe v16 Gettext workflow (`frappe/gettext/translate.py`); no Odoo/OCA counterpart.
- **Planned Scope**:
  1. Ensure every user-facing Python string is wrapped in `frappe._("...")` and every JS string in `__("...")` (English source) for all DocTypes delivered in Phases 0–4.
  2. Generate `l10n_ec/locale/main.pot`, translate `l10n_ec/locale/es.po`, and compile to `.mo` via `bench generate-pot-file`, `bench update-po-files --locale es`, `bench compile-po-to-mo --locale es`.
- **Exit Criteria**: pot/po/mo pipeline runs clean inside bench; Spanish UI spot-check passes on the delivered DocTypes.

---

### Phase 6: Electronic Invoicing EDI (Sales Invoices, Credit/Debit Notes & Purchase Liquidations)
- **Source Equivalence**: [`OCA/l10n-ecuador` PR #102 (`l10n_ec_account_edi`)](https://github.com/OCA/l10n-ecuador/pull/102) + [`PR #103 (`l10n_ec_credit_note`)](https://github.com/OCA/l10n-ecuador/pull/103).
- **Planned Scope**:
  1. **XSD Schema Validator & XML Builders (`l10n_ec/sri/xml_builder.py` & `l10n_ec/sri/xsd/`)**:
     - Bundle official SRI XSD schemas (`factura_V2.1.0.xsd`, `NotaCredito_V1.1.0.xsd`, `NotaDebito_V1.0.0.xsd`, `LiquidacionCompra_V1.1.0.xsd`).
     - Pure Python XML generation and `lxml.etree.XMLSchema` validation testable in Ring 1 (`< 1s`).
  2. **`SRI Electronic Voucher` DocType & Background Worker**:
     - Tracks state machine (`Generated` → `Signed` → `Received` → `Authorized` / `Returned` / `Rejected`) for ERPNext `Sales Invoice` (regular, return/credit note, debit note) and `Purchase Invoice` (when `SRI Document Type == 03` Purchase Liquidation).
     - Enqueues asynchronous submission and authorization polling via `frappe.enqueue(..., enqueue_after_commit=True)`.
  3. **RIDE Print Format & Automated Customer Email**:
     - Jinja/Typst/WeasyPrint RIDE (`Representación Impresa de Comprobante Electrónico`) with barcode of the 49-digit `claveAcceso` and attached authorized `.xml` + `.pdf`.
  4. **Invoicing Business Rules**:
     - Enforce the `Consumidor Final` (`07`) USD 50.00 amount threshold at invoice validation time (format validation alone lives in Phase 1).

---

### Phase 7: Electronic Withholdings (`Comprobante de Retención` v2.0.0)
- **Source Equivalence**: [`OCA/l10n-ecuador` PR #104 (`l10n_ec_withhold`)](https://github.com/OCA/l10n-ecuador/pull/104).
- **Planned Scope**:
  - `SRI Withholding` DocType (or extension on `Purchase Invoice` / `Payment Entry`) generating `ComprobanteRetencion_V2.0.0.xsd` (`codDoc=07`).
  - Supports multi-tax-support (`docsSustento` / `codSustento`) grouping for Income Tax (`impuesto codigo=1`) and VAT (`impuesto codigo=2`) withholdings on purchase invoices and credit card settlements (`Liquidación de Tarjeta de Crédito`).
  - Automatic GL entry posting against withholding payable/receivable accounts.

---

### Phase 8: Electronic Delivery Note (`Guía de Remisión` v1.1.0)
- **Source Equivalence**: [`OCA/l10n-ecuador` PR #107 (`l10n_ec_delivery_note`)](https://github.com/OCA/l10n-ecuador/pull/107).
- **Planned Scope**:
  - Custom fields and EDI integration on ERPNext `Delivery Note` (`Guía de Remisión`, `codDoc=06`, `GuiaRemision_V1.1.0.xsd`).
  - Carrier (`Transportista`) RUC/identification, license plate (`placa`), start/end dates of transport, origin/destination addresses, and linked `Sales Invoice` / `Stock Entry` support documents (`destinatarios`).

---

### Phase 9: Fiscal & Tax Compliance Reports (`ATS`, `Form 104`, `Form 103`)
- **Source Equivalence**: [`OCA/l10n-ecuador` PR #105 (`l10n_ec_ats`)](https://github.com/OCA/l10n-ecuador/pull/105), [`PR #108 (`l10n_ec_104`)](https://github.com/OCA/l10n-ecuador/pull/108), [`PR #109 (`l10n_ec_103`)](https://github.com/OCA/l10n-ecuador/pull/109).
- **Planned Scope**:
  - **Anexo Transaccional Simplificado (`ATS`)**: Generates monthly `AT{mmaaaa}.xml` and `.zip` archive covering purchases (`compras`), sales (`ventas`), exports (`exportaciones`), and annulled vouchers (`anulados`), validated offline against `ats.xsd`.
  - **SRI Form 104 (VAT Declaration)** & **SRI Form 103 (Income Tax Withholding Declaration)**: Frappe Script Reports aggregating tax bases and withholdings by official SRI casillero codes.
