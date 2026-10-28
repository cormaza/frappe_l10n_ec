# Demo en español + validación de traducciones + capturas ajustadas

Rehacer las 23 capturas de `docs/wiki/img/` sobre el seed `Demo Ecuador` con idioma español, validar en runtime que nuestras traducciones cargan, y reencuadrar sin blancos laterales.

## Specs

- S1: "seed de una empresa con la configuración del idioma en español, para que las capturas sean en español".
- S2: "valides que todas las traducciones que nos pertenecen esten bien cargadas".
- S3: "aproveches el espacio y no dejes columnas largas con espacios en blancos laterales".

## Tasks

- T1: Explorar seed, páginas wiki (rutas de cada captura) y tooling disponible — route: inline — commit: —
- T2 (S1): Seed fija `language = es` en Administrator/usuarios demo + compila `es.mo` en el flujo demo — route: inline — commit:
- T3 (S2): Test Ring 1 de completitud de `es.po` (todo msgid propio traducido salvo allowlist core) — route: inline — commit:
- T4 (S1): Tooling de capturas (`dev/shots.py`, playwright + chrome del sistema, login, viewport ajustado) — route: inline — commit:
- T5 (S1): Retomar las 23 capturas en español — route: inline — commit:
- T6 (S3): Revisar cada captura (español visible, sin blancos laterales) y ajustar wiki si cambia texto — route: inline — commit:
- T7: Verificación final (Ring 1 verde, `es.mo` cargado en runtime, capturas en repo) + commit — route: inline — commit:

## Log

- L1 (2026-10-28, verbatim): "bien, he visto las capturas y estan bien, pero preferiria que la hagas con un seed de una empresa con la configuración del idioma en español, para que las capturas sean en español, y valides que todas las traducciones que nos pertenecen esten bien cargadas, ademas quisiera que aproveches el espacio y no dejes columnas largas con espacios en blancos laterales"
- L2: `demo.sh reset` ya fija `System Settings.language = es`; las capturas en inglés vienen del `language` del usuario. `es.po`: 790 traducidos, 1 sin traducir (`Accounts User`, rol de core, excluido por convención).
- L3 (diagnóstico T1 con capturas vistas): la sesión demo YA está en español (core + labels propios traducidos). Leaks reales en inglés: label/description `Supplier Auth Number` (custom_fields.py:299) y description `SRI Tabla 23 IVA withholding concepto withheld...` (custom_fields.py:125) — ambos msgid EXISTEN en `es.po` con msgstr ES. Causa raíz: no hay ningún `es.mo` compilado en bench (el flujo demo nunca corre `compile-po-to-mo`), así que nada propio carga en runtime. Fix S2 = compilar `.mo` + `clear-cache` en el flujo demo y test Ring 1 de completitud del `.po`. S3 confirmado: tabla ATS recortada con `...` y gran blanco lateral derecho; formularios a 1600px con aire lateral.
- L4 (cierre): 23/23 capturas en español a 1366px, cero inglés propio (verificadas una por una). S2: `test_i18n.py` + ciclo bench (`generate-pot-file`→`update-po-files`→traducir→adoptar) sumó 8 msgids (Withholding Slip, Tariff Rate, SRI Reimbursement, Batch IR/IVA, Dates/Payment/Source); `main.pot`/`es.po` adoptados como canónicos (con churn de rewrap). S3: anchos ATS 340/210/130/115/105/255, 104 570/120/45/105/100/95, 103 560/90/135/100/130; badge `Validador ats.plugin.1.19.0` con sidecar de compose. Lecciones: `bench serve` sin `--site` resuelve otro sitio (pineado en `dev/demo.sh serve` + nota en LOCAL_DEMO); `update-po-files` no regenera el POT (correr `generate-pot-file` antes); no hubo prunes (155/155 solo rewrap). `dev/shots.py` queda como tooling (resolución dinámica por API, viewport 1366, modales como elemento).
