# E-Invoicing Known Issues & Hardening Roadmap

Gap analysis of `l10n_ec` electronic invoicing against the current SRI
requirements (<https://www.sri.gob.ec/facturacion-electronica>, ficha
tecnica v2.22 read locally + OCA `l10n-ecuador` PRs #105/#108/#109 as
cross-reference). Our implementation started from `cuymo/
facturacion-electronica-ec` + OCA assumptions; each item below states its
evidence and severity.

## Verified current (not gaps)

- **XAdES-BES RSA-SHA1**: ficha mandates `rsa-sha1`/`sha1`; our signer
  matches. No migration needed.
- **Offline scheme + access key**: reception-proven live on SRI pruebas
  across all six document types (latest: October 2026).
- **XSD versions** (`factura` 1.1.0, `retencion` 2.0.0 ATS, `guia`
  1.1.0, debito 1.0.0, liquidacion 1.1.0): every version passes SRI
  reception today. OCA annexes citing 2.0.0/2.1.0 cover special
  variants only (rubros de terceros, sustitutiva de guia, negociable),
  not the base factura. Watch ficha updates; do not migrate speculatively.
- **Catalogs**: Tabla 24 pagos, Tabla 20/23 retenciones, Tabla 17 IVA
  (incl. diferenciado 8), ICE/IRBPNR ejemplo codes — all sourced.

## H1 — Correctness gaps (high)

1. **Anulacion lifecycle**: SRI Res. NAC-DGERCGC25-00000014 (+00000017
   reform) regulates voiding authorized electronic vouchers. Our states
   end at Authorized/Rejected; no Annulled state, no void flow, and ATS
   `anulados` only covers never-authorized cancels. Needed: void request
   path + state + ATS coverage of authorized-then-voided docs.
2. **Taxpayer-status tags**: builders emit `contribuyenteEspecial` /
   `obligadoContabilidad` but never `agenteRetencion`,
   `contribuyenteRimpe`, or `rise`, so RIMPE/agent taxpayers emit
   incomplete tributaria blocks. Needed: source flags from Company
   master + conditional tags.
3. **infoAdicional**: never emitted. Widely used for emails/descriptions
   and surfaced in RIDE/print contexts. Needed: optional passthrough
   (explicit map, never scraped).

## H2 — Robustness gaps (medium)

4. **Contingency emission** (`tipoEmision` hardcoded `1`): SRI contingency
   flow (type 2 + contingency access keys) for outages is unimplemented.
   Needed: contingency keygen + emission path + resend regularization.
5. **Compensaciones on debit notes**: XSD `compensaciones` block not
   emitted (Res. NAC-DGERCGC16-00000285 context: credit notes with
   compensations). Needed: optional block when data present.
6. **RIDE annexes**: standard RIDE only; subsidy RIDE (Anexo 7) and
   third-party-items formats (Anexo 8) uncovered. Needed on demand.

## H3 — Deferred / out of scope

7. **Factura comercial negociable** (Anexo 11): separate document type
   with its own lifecycle; not requested.
8. **Schema version watch**: re-verify against each new ficha tecnica;
   migrate only on SRI mandate or reception refusal (never speculative).

## Execution

H1 and H2 are independent units (disjoint files per item); H3 is
monitoring only. Each item ships with builder + tests + live reception
proof under the established dual-ring discipline.
