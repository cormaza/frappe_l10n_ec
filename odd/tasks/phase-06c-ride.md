# Phase 6C: RIDE Print Format & Automated Customer Email (Ring 2)

Implements roadmap Phase 6C on `version-16` with direct commits (no PR).

## Specs

- S1: Roadmap Phase 6C scope, quoted verbatim: "RIDE (`Representación Impresa de Comprobante Electrónico`) with barcode of the 49-digit `claveAcceso`.", "Automated customer email with authorized `.xml` + `.pdf` attached."
- S2: Roadmap Phase 6C exit criteria, quoted verbatim: "generated PDF carries a scannable barcode and the authorized XML; email delivers both attachments."
- S3: Locked readings: Jinja Print Format (native path — desk, portal, and `/printview` share the same resolver, so portal support comes free); RIDE shipped as available format, NOT auto-set as global default (per-site decision, documented); barcode via data-URI PNG from a Jinja helper; email auto-sends on `Authorized` with XML+PDF attached, skipping gracefully without a customer email (recorded, never blocking); Sales Invoice RIDE in scope, Purchase/Credit/Debit formats logged as follow-up.
- S4: User confirmations: portal shows RIDE once set as default print format; email carries both files.

## Tasks

- T1 (S1): Barcode helper + Jinja methods + Ring-1 tests. Route: inline. Commit: 41c51ed
- T2 (S1): `SRI RIDE` Print Format fixture + bench render check. Route: inline. Commit: 41c51ed
- T3 (S1): Authorized-email sender + queue proof + tests. Route: inline. Commit: 41c51ed
- T4 (S2): Verify, commit and push to `version-16`. Route: inline. Commit: -
- T4 (S2): Verify, commit and push to `version-16`. Route: inline. Commit: -

## Log

- L1: "vamos con 6c, solo quiero aclarar si el ride tambien saldra en portal? el email incluira el xml?"
- L2: Portal shares the print-format resolver, so RIDE shows there once set as default (not auto-flipped; per-site decision). Email carries signed XML (fid) + RIDE PDF (print_format_attachment, rendered at send). PDF proven via WeasyPrint lib directly (no wkhtmltopdf/chrome binaries here); sender uses standard download_pdf (prod engines). bench execute prints escaped strings — write files from inside for byte-faithful output.
