# Phase 4 Input: Official SCVS Chart Analysis (Full vs Condensed)

Source: `PLAN DE CUENTAS.pdf`, Superintendencia de Compañías, Valores y
Seguros (NIIF financial-statements chart). Extracted locally: 526 text
lines, **336 account lines**. A local copy of the extraction is NOT
committed (official document; working notes only).

## Structure

Five stems, odd-digit leveling (1-3-5-7-9 digits):

- `1` ACTIVO → `101` corriente / `102` no corriente
- `2` PASIVO → `201` corriente / `202` no corriente
- `3` PATRIMONIO NETO → `30` attributable / `31` non-controlling
- Result stems (`41/43` income, `51/52` cost/expense) plus computed
  subtotal groups (`42, 60, 62, 64, 67, 73, 75, 77, 79, 81, 82, 90, 91`),
  cash-flow section (`95-99`, tipo estado 3), equity-change (`99`, tipo 5)
- Columns: SIGNO (P/N/D), TIPO DE CUENTA (T total / D detail),
  TIPO DE ESTADO (1 situation / 2 results / 3 cash flow / 5 equity change)

## Why verbatim-full alone is insufficient for ERPNext

The official chart is a **presentation chart for filing**, not an
operational one. Gaps blocking daily postings and our tax templates:

1. No bank/cash breakdown: `10101` EFECTIVO is a detail leaf, no children.
2. No output/input VAT split: only net `1010501` CRÉDITO TRIBUTARIO (IVA).
3. No withholding detail: only aggregate `2010701` CON LA ADMINISTRACIÓN
   TRIBUTARIA (no VAT/IR withholding payable splits, no ICE/IRBPNR).
4. Computed groups (`42` GANANCIA BRUTA, `60-79` subtotals, `95-99` cash
   flow) are formulas, never postable; importing them as accounts pollutes
   the trial balance.

## ERPNext mapping rules (locked for implementation)

- Stems: `1`→Asset, `2`→Liability, `3`→Equity, `41/43`→Income,
  `51/52`→Expense. Tipo estado `1`→Balance Sheet, `2`→Profit and Loss.
- Official T (total) → `is_group`; official D (detail) → leaf, except
  leaves we extend operationally (become groups, documented per account).
- Computed/cash-flow/equity-change groups (`42, 60-91, 95-99`) are
  **excluded** from the ERPNext tree (filed statements, not postings).
- Operational leaves (~30-40) appended under the correct official parent
  with consistent 7/9-digit numbering: bank/cash under `10101`, VAT
  in/out, withholding payable splits, ICE/IRBPNR, customer/supplier
  control details.

## What a condensed (~80-account) chart loses

1. Exact presentation mapping for Super Cías filing (every T/D line is a
   filing casillero; a condensed chart needs a manual crosswalk).
2. Auditor completeness: missing official groups raise questions on review.
3. The full resultado/flujo/patrimonio sections disappear as reference.
4. Future phases (ATS/103/104 cross-checks) lose their anchor accounts.

## Recommendation

Full official transcription (~336 lines, smaller than feared — one
focused data turn) **plus** the operational extension (~30-40 leaves).
It satisfies "verified NIIF" literally, keeps filing mapping exact, and
makes daily postings possible. Pure-condensed saves one data turn but
pays back in crosswalks and audit friction.
