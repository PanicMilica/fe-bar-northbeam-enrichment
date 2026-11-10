# Databricks App evidence: `northbeam-enrichment-console`
_Collected 2026-11-10 17:48 UTC._

* URL: https://<app-url> (workspace SSO; not public)
* App status: **RUNNING** · compute **ACTIVE** · last deployment **SUCCEEDED**
* Resources bound to the app: `lakebase` (database), `genie-space` (genie_space), `sql-warehouse` (sql_warehouse)
* Runs as service principal `<app-service-principal>`; Postgres grants: SELECT on the synced gold table, SELECT/INSERT on review decisions
* Analyst identity comes from the `X-Forwarded-Email` header and is stored with each decision.

Tabs: **Overview** (KPIs from Lakebase) · **Review queue** (approve / correct / reject → `review.review_decisions`) · **Ask Genie** (Genie Conversation API).
Below, the exact SQL the app runs, executed against the same Lakebase database:

## Overview KPIs (tab 1)
```sql
SELECT count(*) AS products,
         count(*) FILTER (WHERE NOT needs_review OR human_verified) AS enriched,
         count(*) FILTER (WHERE needs_review AND NOT human_verified) AS to_review,
         count(*) FILTER (WHERE human_verified) AS verified,
         round(avg(confidence_score)::numeric, 1) AS avg_conf
       FROM public.gold_product_enrichment
```
| products | enriched | to_review | verified | avg_conf |
|---|---|---|---|---|
| 553 | 348 | 205 | 3 | 70.1 |

## New products per delivery week (tab 1 chart)
```sql
SELECT first_enriched_week AS week, count(*) AS new_products,
         count(*) FILTER (WHERE NOT needs_review) AS auto_enriched
       FROM public.gold_product_enrichment GROUP BY 1 ORDER BY 1
```
| week | new_products | auto_enriched |
|---|---|---|
| 2026W40 | 460 | 294 |
| 2026W41 | 38 | 20 |
| 2026W42 | 55 | 34 |

## Review queue, first 8 rows (tab 2)
```sql
SELECT g.market, g.item_id, g.descriptor_en, g.evidence_tier, g.matched_product_name,
         g.protein_g_per_bar, g.segment, g.confidence_score
       FROM public.gold_product_enrichment g
       LEFT JOIN (SELECT DISTINCT market, item_id FROM review.review_decisions) d ON d.market = g.market AND d.item_id = g.item_id
       WHERE g.needs_review AND NOT g.human_verified AND d.item_id IS NULL
       ORDER BY g.confidence_score ASC, g.item_id LIMIT 8
```
| market | item_id | descriptor_en | evidence_tier | matched_product_name | protein_g_per_bar | segment | confidence_score |
|---|---|---|---|---|---|---|---|
| ES | ES-100024 | Protein Bars 35g 1 unit | none |  |  |  | 0 |
| ES | ES-100037 | PROTEIN BAR CHOC BROWNIE 60G 1UN | none |  |  |  | 0 |
| ES | ES-100039 | Muesli bar strawberries good bio 25g 1 unit | none |  |  |  | 0 |
| ES | ES-100049 | BARRINOLAS 48G 1UN | none |  |  |  | 0 |
| ES | ES-100074 | Cereal Bars with Grains and Almonds Carrefour France 25g 4 Units | name_match | Protein bar | 4.0 | NOURISH | 0 |
| ES | ES-100147 | Oat Muesli with Cranberries and Pumpkin Seeds Hero 35g 1unit | none |  |  | NOT A SNACK BAR | 0 |
| ES | ES-100186 | BREAKFAST BAR ALMONDS X6 40G 1UN | none |  |  |  | 0 |
| ES | ES-100239 | BLACK CHOCOLATE 21G 6UN | none |  |  | NOT A SNACK BAR | 0 |

## Recent decisions saved from the app (tab 2)
```sql
SELECT market, item_id, action, field, ai_value, corrected_value, reviewer_email, reviewed_at, applied
       FROM review.review_decisions ORDER BY reviewed_at DESC LIMIT 20
```
| market | item_id | action | field | ai_value | corrected_value | reviewer_email | reviewed_at | applied |
|---|---|---|---|---|---|---|---|---|
| ES | ES-100019 | reject | segment |  |  | analyst@northbeam.example | 2026-11-10 17:15:27.811693+00:00 | True |
| ES | ES-100015 | correct | kcal_per_bar | nan | 150.0 | analyst@northbeam.example | 2026-11-10 17:15:15.352134+00:00 | True |
| ES | ES-100015 | correct | protein_g_per_bar | nan | 16.0 | analyst@northbeam.example | 2026-11-10 17:15:15.304630+00:00 | True |
| ES | ES-100015 | correct | segment |  | HIGH PROTEIN | analyst@northbeam.example | 2026-11-10 17:15:15.246487+00:00 | True |
| ES | ES-100000 | approve | segment | ENERGY | ENERGY | analyst@northbeam.example | 2026-11-10 17:14:28.907705+00:00 | True |

## Deployment log (last lines)
```text
2026-11-10T16:16:53Z [BUILD] [INFO] Deployment successful
2026-11-10T17:47:56Z [BUILD] [INFO] Running security scan on source
2026-11-10T17:47:56Z [BUILD] [INFO] Starting app with command: [streamlit run app.py --server.headless true]
2026-11-10T17:47:58Z [BUILD] [INFO] Deployment 01f1dd2ed9f61703b119979452d8081c ended in 3.999904247s
2026-11-10T17:47:58Z [BUILD] [INFO] Deployment successful
2026-11-10T17:48:03Z [BUILD] [INFO] Security scan completed: no findings
```