# IVA 8% for Holiday Tourism Services — Evidence and Implementation

Ecuador temporarily reduces IVA to 8% on tourism services during decreed
holidays. This document collects the official sources and records how
`l10n_ec` implements the rate.

## Official sources

- SRI, tourism tax benefits hub (base legal, conditions, e-invoicing code):
  <https://www.sri.gob.ec/beneficios-tributarios-para-el-sector-turistico>
- SRI offline e-invoicing ficha tecnica v2.22, Tabla 17 (rate codes) and
  Tabla 18 (ICE tariffs): SRI portal facturación electrónica.
- Ministerio de Turismo, 8% holiday reduction notices (per-holiday decrees).
- Executive decrees per holiday (examples): Decreto 339 (2022 carnaval +
  semana santa), Decreto 429 (RO-674, October 2024), Decreto 465 (August
  2026 feriado), SRI bulletins 009 (carnaval) and 026 (24 de mayo).
- LRTI Art. 58 (ICE is part of the IVA base); Ley de Turismo Art. 5
  (tourism activities); NAC-DGERCGC22-00000010 (application rules).

## Rate rule

- The President may cut IVA from 12% to 8% on Art. 5 tourism services
  (lodging, food & beverage, tourist transport, agencies/events, casinos),
  at most 12 days per year, per Executive Decree with exact dates.
- Provider must be in the Registro de Turismo with LUAF; service rendered
  on decreed dates with valid vouchers (airline tickets excepted by nature).
- Mixed tariffs on one voucher are allowed (one line per rate, or one
  voucher per rate); services spanning reduced/non-reduced dates must split.

## Electronic invoicing code (SRI Table 17)

| IVA | codigoPorcentaje |
|---|---|
| 0% | 0 |
| 12% | 2 |
| 14% | 3 |
| 15% | 4 |
| No objeto | 6 |
| Exento | 7 |
| **Diferenciado (5%, decreed 8%, …)** | **8** |

Code `8` covers every non-standard rate; the `tarifa` field carries the
actual percent. No new SRI code was needed for the 8% holidays.

## Form 104 boxes for reduced rates

Sales `421`, plus `423`/`424` for rate differences vs credit notes;
purchases `520`/`522`, plus `526`/`527` for differences. A dedicated
reduced-rate box was announced as upcoming implementation work.

## Implementation in `l10n_ec`

- `TAX_TEMPLATES`: `Ecuador VAT 8% - Sales/Purchases` (rate 8.0, standard
  VAT accounts; created by `setup_ecuadorian_taxes` like the 15%/5% rows).
- `TEMPLATE_TAX_CODES`: both 8% titles map to `("2", "8")`; `tarifa`
  distinguishes 8.0 from 5.0 at emission.
- Usability note: the template is inert master data until a holiday
  decree activates it; applying it outside decreed dates/activities is a
  user (not system) decision, exactly like ICE product tariffs.
