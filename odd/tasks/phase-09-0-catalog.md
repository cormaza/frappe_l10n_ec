# Phase 9.0 — Complete Fiscal Catalog (Phase 9 prerequisite)

## Specs
- S1: Official IR/IVA withholding concepto table (XML `codigoRetencion` values + rates + 2026-03-01 vigencia), replacing per-call code maps. (Casillero pairs moved to 9B: they serve the 103 report only.)
- S2: ICE/IRBPNR line-tax mapping (SRI codes `3`/`5`) with Item Tax Templates and ledger accounts; product-specific ICE rates stay user-configured.
- S3: SRI Payment Method table (Tabla 20) bridged from ERPNext Mode of Payment (today everything emits as `01`).
- S4: Verify, commit, and push to `version-16` with dual-ring tests.

## Tasks
- T1 (S1/S2/S3): Research official SRI tables (retención conceptos, casilleros 103, ICE/IRBPNR, Tabla 20) with sourced evidence. Route: parent (web). Commit: n/a (research, evidence in L2)
- T2 (S1): Withholding conceptos module + migrate code maps + tests. Route: worker. Commit: ae52b57
- T3 (S2): ICE/IRBPNR mapping mechanism (explicit per-template `extra` map in `tax_codes_for_template`; real tariff rate codes stay per-product user configuration) + tests. Route: parent-inline. Commit: ae52b57
- T4 (S3): Tabla 20 + Mode of Payment bridge + tests. Route: worker. Commit: ee3ed26
- T5 (S4): Verify, commit and push to `version-16`. Route: parent. Commit: ee3ed26

## Log
- L1: "adelanta vamos con la 9.0"
- L2 (T1 evidence): IR conceptos Tabla 20 SRI (25 codes: 303/303A/304/304A/304C/304D/307-312/319/320/322/323/332/343/343A-C/344A-B/3440/3482, vigencia 2026-03-01 NAC-DGERCGC26-00000009; quipuy + deley + SRI resolution); IVA conceptos Tabla 23 (1:30% 2:70% 3:100% 7:0% 8:0% 9:10% 10:20% 11:50%, unchanged 2026); pagos Tabla 24/ATS (01/15/16 debito/17/18/19 credito/20/21); IRBPNR $0.02/bottle (factuplan + vigente.ec + SRI page); OCA PRs #105/#108/#109 carry reference docs (ats.xsd + ats_catalog_*.xml + withholding concepts/rates XML + 103/104 forms; /tmp/oca-ref/). CORRECTIONS to prior assumptions: payments are Tabla 24 (not 20); 16=debito/19=credito (not 16=credito); IVA codes are 1/2/3/7/8/9/10/11; OCA 401xx/500s are ATS/exterior namespaces, NOT XML codigoRetencion. SCOPE ADJUSTMENT: casillero pairs move to 9B (they serve the 103 report only; ATS/vouchers use concepto codes); 9.0 ships conceptos + rates + vigencia.
- L3: 9.0 closed. Live proof: voucher 001-001-000000003 emitted with formaPago 19 end-to-end (RECIBIDA then FIRMA INVALIDA). MoP custom field installed on bench. 45 new es translations. Parent-owned fixes: accents on concepto descriptions; cancelled taxless SI-00003 (setup error, no template).
