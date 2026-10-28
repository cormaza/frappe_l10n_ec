# Edge-case resilience tests (packs A–F)

Pin extreme emit/receive combinations as Ring-1 tests: happy path plus
every fail-loud rejection naming the culprit. Pure `l10n_ec/sri/` + report
readers; no bench needed.

## Specs

- S1: "ajustar las pruebas, para abordar edge cases".
- S2: "las posibilidades en los distintos documentos que puedo emitir,
  recibir, combinaciones extremas".
- S3: "determinar que vale la pena dejar como prueba de la resiliencia
  de lo implementado".
- S4 (scope answers): packs A–F all, RED completo (happy + all fail-loud
  rejections per case).

## Tasks

- T1 (S1/S2, pack A): single 01 mixing 15% + 0% + exempt + no-object +
  ICE across lines; each base lands in its own 104/ATS bucket. Route: unit. Commit: 3df1747
- T2 (S1/S2, pack B): supplier 04/05 XML explicitly rejected by reception
  mapper (fail loud, never a purchase). Route: unit. Commit: 44e53d7
- T3 (S1/S2, pack C): annulled 03/06/07 feed ATS anulados with
  number+auth (01 already pinned). Route: unit. Commit: 5ad51cc
- T4 (S1/S2, pack D): settlement with 2 partidas/rates; DAI crosscheck
  fails on the second naming the rate (T7 blind). Route: unit. Commit: b99d5b5
- T5 (S1/S2, pack E): received batch over 3 SIs (mixed IR/IVA), one
  unmatched left manual, partial payment never over-allocates. Route: unit. Commit: 2ddeda3
- T6 (S1/S2, pack F): mixed month with 8% holiday + 15% in 104
  (factor 563) side by side. Route: unit. Commit: 7812a08

## Log

- L1 (original request, verbatim): "ahora quisiera ajustar las pruebas,
  para abordar edge cases, ayudame a determinar las posibilidades en los
  distintos documentos que puedo emitir, recibir, combinaciones extremas,
  para determinar que vale la pena dejar como prueba de la resiliencia
  de lo implementado".
- L2 (scope): all packs A–F, RED completo.
