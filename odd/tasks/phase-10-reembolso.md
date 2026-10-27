# Phase 10 — Liquidación de compras por reembolso de gastos + ATS

Objetivo: modelar reembolso como entidad independiente (ambos roles) con bloque propio en emisión y ATS.
Branch: `version-16` → feature `feat/reembolso-ats` (crear al implementar). Estrategia: `ask-on-risk`, slices ~400 líneas. Runner: `.venv/bin/pytest -v -W error` + `pre-commit` + DIMM.

## Specs

- S1: "liquidacion de compras por reembolsos de gastos, tiene su estructura propia" — bloque `reembolsoDetalle` en factura/liquidación + 12 campos `reembolsoType` en ATS + `totbasesImpReemb`. Checks: XSD `factura_V1.1.0`, `LiquidacionCompra_V1.1.0`, `ats.xsd` validan; RIDE muestra lo emitido.
- S2: "afecta la forma en que se elabora el ats" — `detalleCompras` con `totbasesImpReemb?` + `reembolsos?` en orden XSD; bases reembolsadas no suman a `baseImpGrav/baseNoGraIva/baseImpExe/montoIva` propios. Checks: `collect_purchase` + `_render_compra` + DIMM verde.
- S3: "1 los 2" — ambos roles: (a) intermediario emite `41/47/48` con reembolsos, compra origen con sustento `08`; (b) mandante registra `41` recibida con sustento según naturaleza (01-07). Checks: `classify_purchase` acepta `41/47/48/21`; validación cruzada sustento×tipo.
- S4: "2 deberia ser una entidad independiente" — child DocType `SRI Reembolso Detalle` independiente (no ítems), linkable a Purchase/Sales Invoice + voucher. Checks: DocType JSON + `test_*.py` en clase `UnitTestCase/IntegrationTestCase`.
- S5: "3 calculado, editable pero quizas un valor forzado por el usuario como un opt-in" — `totbasesImpReemb` calculado por defecto; override manual solo con opt-in explícito `sri_reembolso_override` + auditoría; fail-loud si no cuadra y no hay opt-in. Checks: RED por descalce + GREEN con override.

## Tasks

- T1 (S1,S3,S4,S5): Modelo `SRI Reimbursement Detail` + validación sustento×tipo + `totbasesImpReemb` calculado/opt-in. Route: inline. Status: done (467 passed + pre-commit). Commit: —
- T2 (S1,S3): Emisión factura/liquidación con `<reembolsos>` + parse + RIDE. Route: worker. Status: done (515 passed + ruff clean). Commit: —
- T3 (S2,S3,S5): ATS collector/builder/reader con `reembolsos` + `totbasesImpReemb`. Route: worker. Status: done (483 passed + pre-commit). Commit: —
- T4 (S2,S5): Contabilización + Form 104 + demo DIMM. Route: parent. Status: done (517 passed + pre-commit; bench Oct-2026: 11 compras incl. 41 con 2 reembolsos totbases 250.00 + 08; 104 ledger inmune por diseño). Commit: —
- T5 (S1-S5): Triangulación ATS↔104 + docs `FIND_ATS_103_104.md` + `02-factura-compra.md`. Route: inline. Status: done (517 passed + pre-commit; bench Oct-2026 verificado). Commit: —

## Log

- L1: "hay un tema importante a implementar ayudame a definir la implementacion, y es la liquidacion de compras por reembolsos de gastos, tiene su estructura propia y afecta la forma en que se elabora el ats, evalua su diseño e implementacion"
- L2 (2026-10-26): Decisiones usuario — "1 los 2, 2 deberia ser una entidad independiente, 3 calculado, editable pero quizas un valor forzado por el usuario como un opt-in". Alcance: ambos roles; child independiente; total calculado con override opt-in.
- L3 (2026-10-26): T2 naming — XSD factura/liquidación usa `totalImpuestoReembolso` (no `totalMontoIvaReembolso`); implementado per XSD. `codDocReembolso` único por factura (códigos mixtos fallan). `supplier_type` default 01; ICE exige desglose explícito.
- L4 (2026-10-26): Incidente demo-reset — fresh `install-app l10n_ec` fallaba con `Default value for sri_sustento_code must be in the list of options` (default `02` vs opciones con leyenda; Frappe 16.52 `check_illegal_default` vía Property Setter). Fix: default `02 - Sin crédito tributario` + test `test_select_defaults_belong_to_options` (todos los Select con default deben pertenecer a options). Consumidores usan `sri_code()` así que el cambio es seguro.
- L5 (2026-10-26): job-2 reset+seed OK (fix válido); falló solo la sonda (`bench execute` evalúa una expresión, no statements). Job-3 + fix `resolve_reimbursement_total` (Currency bench trae `0.0` = sin override). Bench Oct-2026 verificado: 11 compras (01×8, 04×1, 05×1, 41×1), `41` con 2 reembolsos `totbasesImpReemb 250.00`, XML válido XSD. 103 sin cambios (solo 07); 104 inmune (ledger por ítem). T5 docs actualizados. Serie completa: 517 passed + pre-commit limpio. Sin commitear (decisión tuya).
- L7 (2026-10-26): DIMM sidecar `cormaza/ats-validator:1.3.0` levantado local (puerto 127.0.0.1:8080, plugin 1.19.0 = EXPECTED, no stale). `validate_month(Demo Ecuador,2026,10)` → verdict `valid`, messages [], talón `/private/files/AT102026-talon.html`. Talón confirma 41×1 (BI 100.00, IVA 15.00, reembolso fuera de bases) y 01×8/04/05. Emisión offline válida XSD: factura 01 staged + retención 07 → `validate_against_xsd` true en bench. Reembolsos en emisión cubiertos por tests T2 Ring-1 (XSD 1.1.0). Autorización SRI en línea no probada (cert demo autofirmado).
