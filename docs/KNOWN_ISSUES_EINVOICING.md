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
3. **infoAdicional**: DONE — central `SRI Additional Information` entity
   (company-scoped) + transactional `sri_info_adicional` tables on
   Quotation/Sales Order/Sales Invoice + lazy resolution (SI, order,
   quote, central; nearest wins; 15-row cap) + factura emission with
   live proof.

## H2 — Out of scope (will not be done)

Compensaciones and RIDE annexes are sector-special cases (compensation regime, subsidized fuels): implement only on sector demand. Parked.

4. **Compensaciones on debit notes**: XSD `compensaciones` block not
   emitted (Res. NAC-DGERCGC16-00000285 context: credit notes with
   compensations). Needed: optional block when data present.
5. **RIDE annexes**: standard RIDE only; subsidy RIDE (Anexo 7) and
   third-party-items formats (Anexo 8) uncovered. Needed on demand.

## H3 — Dropped (not to be done)

Contingency emission (unused in practice) and factura comercial
negociable (Anexo 11, separate lifecycle, not requested) are dropped.
Schema version watch continues as monitoring only.: re-verify against each new ficha tecnica;
   migrate only on SRI mandate or reception refusal (never speculative).

## Execution

H1 and H2 are independent units (disjoint files per item); H3 is
monitoring only. Each item ships with builder + tests + live reception
proof under the established dual-ring discipline.
