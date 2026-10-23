# `l10n_ec` Status: Inventory, Known Issues, Deliberate Non-Goals

Branch `version-16`, Frappe/ERPNext v16, Python 3.14. As of `3b3b863`:
**420 tests collected** (Ring-1 `pytest -W error` + bench `run-tests`),
**509 msgids** (`es.po`, `msgfmt` clean), 125 work-unit commits.
Companion docs: `ROADMAP.md` (phased plan), `ROADMAP_POS_ECOMMERCE.md`,
`FIND_ATS_103_104.md` (operator guide + live triangulation),
`KNOWN_ISSUES_EINVOICING.md` (e-invoicing gap detail), `LOCAL_DEMO.md`.

## 1. Feature inventory (all verified live unless noted)

**SRI pure domain layer (`l10n_ec/sri/`, zero top-level `frappe` imports).**
XAdES-BES RSA-SHA1 signing (`signer.py`), 49-digit access keys (`access_key.py`),
offline/online SOAP (`soap_client.py`), XML builders + XSD validation for
01/03/04/05/06/07 (`xml_builder.py`, `xsd/`), voucher states incl. `Annulled`
(`voucher_states.py`), access-key barcode (`barcode.py`), RUC/CI validation
(`identification.py`, `python-stdnum`), SRI registry soft-check
(`ruc_lookup.py`: stdnum → `estadoTributario` 4s timeout → reject with cause;
positives cached 7d), tax-code mapping incl. IVA 8% diferenciado
(`tax_codes.py`), withholding conceptos 176 codes (`withholding_concepts.py`),
IR/IVA concepto tables, Tabla 24 payments (`payment_methods.py`), sustento
guard (`sustentos.py`), ATS collect/build (`ats_collector.py`,
`ats_builder.py`, `ats.xsd`), ATS/form/103/104 presentation layouts
(`ats_layout.py`, `form104_layout.py`), Form 103/104 collectors
(`form103.py` residentes + exterior, `form104.py` 128 boxes),
treaty rates (`treaties.py`: ES CDI + 25%/37% domestic).

**Catalogs (6 DocTypes + fixtures with `name` keys).** SRI Signature,
Identification Type, Document Type, Payment Method (Tabla 24), Tax Support
(Tabla 5), Emission Point + Sequence, Electronic Voucher, Additional
Information. Installable via `hooks.fixtures`.

**Validation hooks.** Party ID validation with per-contact override flag
(`sri_skip_id_validation`); CF USD 50 threshold on Sales Invoice, per-ticket
on POS Invoice, consolidated exemption (per-ticket check via backlink),
anticipated on shop orders; IVA deduction-row enforcement; sustento guard;
tax-row descriptions in SRI pattern (`IVA 15% (4)`, `Exento (7)`...).

**Chart + taxes.** 315-node NIIF chart + 9 leaves, 14 tax templates
(15%/8%/5%/0%/exento/no-objeto, ICE, IRBPNR), 6 IR withholding seeds
(IVA never seeded — native guard would double-count).

**E-invoicing emission (`voucher_flow.py`).** 01/03/04/05/06/07 through
generate/sign/submit/poll with XSD-first fail-loud; per-ticket batch for
CF consolidated over 50; origin rule (single CF voucher > 50 refused);
channel lock (desk/POS/shop-only points, row-locked sequential bump);
RIDE + email for all types (01/04/05/06/07 from emitted XML, embedded
DIMM talón dialog for ATS).

**Reports (desk, Spanish).** SRI ATS (detail grids + subtotals + ZIP
download + DIMM validation + staleness badge), SRI Form 103 (per-concepto
residentes + exterior section + 497/498), SRI Form 104 (DIMM blocks,
bruto/neto/impuesto + sign markers). Ecuador workspace with shortcuts.

**ATS + DIMM sidecar (separate repos).** `ats_validator_rest`
(SRI plugin 1.19.0, `/version`, fail-loud 500s, token gate) +
`docker_ats_validator` (`cormaza/ats-validator:1.3.0` public). Frappe calls
it for deep validation; staleness is version-compared, never implied.

**POS + shop.** Emission point per POS Profile, session stamp, CF rules
both modes, merge-identity guard, shop point inheritance QT→SO→SI,
shop-only channel, shopper-ID API. Webshop integration is guarded
(absent app = silent skip); upstream `frappe/webshop#412` removes its
dead `payments` dep.

**Demo (`dev/demo.sh`).** Idempotent seed: 2 companies (EC/CO), 4+ parties,
9 PIs, 4+ SIs, DN, payments/JEs, 3 staged resident 07s + 3 exterior 07s
(ES/US/PA), 1 Generated 01, emission points (desk/POS/shop), POS profile,
webshop wiring when present. USD everywhere.

## 2. Known issues (all with evidence, none silent)

1. **Self-signed ceiling.** Demo signs with a test P12: SRI answers
   `FIRMA INVALIDA`, so demo vouchers live in `Rejected`/`Generated`.
   Authorized states in demo are staged fiction (documented per case).
   Needs a real cert for end-to-end authorization proofs.
2. **SRI móvil flakiness.** `estadoTributario` answers in 0.1s or times
   out; WAF HTML with HTTP 200 happens (their own client documents it).
   Design absorbs it (verdicts, short timeout, override flag).
3. **Test RUCs are registry-unknown.** `1790016919001` et al. fail
   stdnum *and* come back unknown — correct behavior, but don't use them
   as "valid" fixtures.
4. **Reseed stock fragility.** Re-running `seed` on a used demo dies
   with `NegativeStockError` (WIDGET-ZERO); `reset` is the clean path.
   Worker absent → 600-job queue pileup (`QueueOverloaded`); run
   `dev/demo.sh worker` or flush in demo.
5. **Infra duality.** After a host reboot, `docker start` the existing
   `l10nec-*` containers (data volumes); the compose stack is a parallel
   empty one. Bench serve port is 8001 in this repo's flow (`demo.localhost`
   404s; use `Host: demo`).
6. **Upstream blockers.** `frappe/webshop#412` (dead dep), webshop
   frontend build fails in this env (backend verified only),
   `payments` v14 unmigratable on v16. Nothing of ours depends on them
   at runtime (guarded).
7. **Proof hygiene.** Staging `Authorized` without `finally`-revert
   contaminated ATS once (phantom 104/105/107). Rule: stage with revert,
   or stage only via seed (durable, documented fiction).
8. **Formatter false-red.** `pre-commit` ruff-format occasionally fails
   pre-`add` then passes clean on HEAD. Run it before staging, not after.

## 3. Deliberately out (with reopen conditions)

- **Contingency + factura negociable (H2).** Unused/not requested.
  Reopen on SRI mandate or sector demand.
- **Compensaciones/annexes (H2/H3 sectorial).** Sector-only scope.
- **Exterior ATS section + exterior regime auto-mapping.** No SRI
  paraíso-list vendored; regime is explicit input, rates sourced-only.
  Reopen with the versioned SRI list.
- **Native validator port.** The DIMM engine stays a sidecar; only
  deterministic single rules get ported with sources. Reopen on proven
  per-rule parity.
- **P0 settings flags.** Everything ships direct like the rest of the
  app. Reopen for mixed companies needing per-company toggles.
- **Portal 349/399/499/103-subtotals, ICE-input account, exterior
  104 IVA.** No ledger input distinguishes them; computing would
  misstate. Reopen with distinguishing inputs.
- **`Odoo-style auto_install`.** Doesn't exist in Frappe; flags +
  guards are the pattern. Nothing to reopen.
- **Per-ticket default emission.** Only CF-over-50 consolidations
  split; everything else emits one voucher. Reopen on accountant demand.
- **Guessing unknown conceptos/rates/boxes.** Fail-loud everywhere
  (unknown concepto/code/sustento/regime/treaty pair raises). Never
  reopen: this is the house rule, not a gap.
