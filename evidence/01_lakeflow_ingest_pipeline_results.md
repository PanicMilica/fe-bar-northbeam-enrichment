# Evidence 1 · Lakeflow ingest pipeline `northbeam_ingest` (executed)
Pipeline: [src/pipeline/ingest.py](../src/pipeline/ingest.py) · serverless Lakeflow Declarative Pipeline (`dlt`), Auto Loader + AUTO CDC.
Source: pipeline event log, `event_log('<pipeline_id>')`, queried 2026-11-10 on the SQL warehouse.

## Weekly deliveries arrive → only the new file is read (Auto Loader) → silver grows incrementally
| delivery week uploaded | pipeline update (UTC) | state | silver_item_first_seen rows after update |
|---|---|---|---|
| 2026W40 (ES 230 + US 230) | 2026-11-10 15:48 (full refresh) | COMPLETED | 460 |
| 2026W41 (ES 241 + US 242) | 2026-11-10 17:18 | COMPLETED | 498 (+38 new items) |
| 2026W42 (ES 259 + US 261) | 2026-11-10 17:27 | COMPLETED | 553 (+55 new items) |

`silver_public_reference` (public Open Food Facts snapshot): 1,160 raw rows → **1,155** after `expect_or_drop`.

## Data-quality expectations (from the event log, summed over all updates)
| flow | expectation | type | passed | failed |
|---|---|---|---|---|
| silver_product_item | valid_item_id | expect_or_drop | 1923 | 0 |
| silver_product_item | valid_week | expect_or_drop | 1923 | 0 |
| silver_product_item | has_descriptor | expect (warn) | 1923 | 0 |
| silver_product_item | public_barcode | expect (warn) | 1509 | **414** |
| silver_public_reference | valid_gtin | expect_or_drop | 15080 | 0 |
| silver_public_reference | has_nutrition | expect_or_drop | 15080 | 0 |
| silver_public_reference | plausible_nutrition | expect_or_drop | 10395 | **45** |

`public_barcode` failures are expected: they are private-label / missing-barcode rows, which the GenAI tier resolves by name.
`plausible_nutrition` dropped public records with impossible values (e.g. 28,000 kcal per 100 g).

## Silver product master after week 42 (one row per market + item, AUTO CDC SCD1)
| market | first seen week | items | with public barcode | private label |
|---|---|---|---|---|
| ES | 2026W40 | 230 | 178 | 29 |
| ES | 2026W41 | 18 | 13 | 4 |
| ES | 2026W42 | 23 | 18 | 2 |
| US | 2026W40 | 230 | 187 | 34 |
| US | 2026W41 | 20 | 15 | 4 |
| US | 2026W42 | 32 | 26 | 5 |
