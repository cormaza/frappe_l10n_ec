# Phase 6A: XSD Schemas & XML Builders (Pure Python, Ring 1)

Implements roadmap Phase 6A on `version-16` with direct commits (no PR).

## Specs

- S1: Roadmap Phase 6A scope, quoted verbatim: "Bundle official SRI XSD schemas (`factura_V2.1.0.xsd`, `NotaCredito_V1.1.0.xsd`, `NotaDebito_V1.0.0.xsd`, `LiquidacionCompra_V1.1.0.xsd`) under `l10n_ec/sri/xsd/`.", "Pure Python XML generation (`l10n_ec/sri/xml_builder.py`) with `lxml.etree.XMLSchema` validation, testable in Ring 1 (`< 1s`)."
- S2: Roadmap Phase 6A exit criteria, quoted verbatim: "one example XML per voucher type validates against its official XSD; suite green with zero `frappe` imports."
- S3: Split decision: user chose "Partir como propuesto" (6A→6B→6C sequential, 6D independent).

## Tasks

- T1 (S1): Source the four official XSDs and bundle under `l10n_ec/sri/xsd/`. Route: inline. Commit: f0ecdc3
- T2 (S1): `xml_builder.py` + Ring-1 tests (one valid example per voucher type). Route: inline. Commit: 113a7dc
- T3 (S2): Verify (`pytest -W error`, `pre-commit`), commit and push to `version-16`. Route: inline. Commit: -

## Log

- L1: "bien, ahora quiero analizar la fase 6 y evaluar si es adecuado correrla tal como esta, o vale la pena separarla para ir revisando de a poco, ayudame a juzgarlo"
- L2: Analysis favored 6A–6D split (mixed rings, chained deps, missing exit criteria); user approved split-as-proposed and starting with 6A.
- L3: Roadmap specified `factura_V2.1.0.xsd`, but the SRI base invoice schema is V1.1.0 (2.x flavors cover special cases like third-party items); corrected roadmap to `factura_V1.1.0.xsd`. XSDs sourced from the MIT-licensed `cuymo/facturacion-electronica-ec` repo (6/6 document types authorized end-to-end against SRI pruebas in 2026 with these exact schemas); vendor/ and sdk/ copies verified byte-identical, all parse clean with lxml.
