# Evidence 2 · Unity Catalog governance (executed)
Code: [src/gold/00_gold_governance.sql](../src/gold/00_gold_governance.sql) runs as job task `setup_and_governance` every week (idempotent).
Source: `information_schema` and `system.access.table_lineage`, queried 2026-11-10.

## Every table is in one governed schema `milica_test.fe_bar_northbeam`, with comments
| table | type | comment (from information_schema.tables) |
|---|---|---|
| bronze_delivery_es / _us | STREAMING_TABLE | Raw weekly product deliveries, exactly as received (Auto Loader). |
| bronze_public_reference | STREAMING_TABLE | Public Open Food Facts snapshot of snack bars (ODbL), as downloaded. |
| silver_product_item | STREAMING_TABLE | Standardised product master across markets: one row per market + item, latest delivery wins. |
| silver_item_first_seen | MATERIALIZED_VIEW | First and last delivery week per item; drives the 'new products only' worklist. |
| silver_public_reference | MATERIALIZED_VIEW | Cleaned public product reference: one row per GTIN with per-100 g and per-serving nutrition. |
| gold_product_enrichment | MANAGED | Enriched snack-bar attributes per retailer item ... Synced to Lakebase for the review app. |
| mv_enrichment_kpis | METRIC_VIEW | Enrichment KPIs for Northbeam: coverage, automation rate, review backlog, confidence and segment mix. |
| review_history | MANAGED | Analyst decisions from the review app (via Lakebase), applied to gold. Governed: row filter by market, reviewer masked. |
| evidence / ref_embeddings / run_metrics / evaluation_results | MANAGED | audit trail of candidates · embeddings cache · cost & volume per run · MLflow evaluation history |

Lakebase is governed too: the Postgres database is registered as UC catalog **`northbeam_lakebase`** and the gold
table is a UC **synced table** (`northbeam_lakebase.public.gold_product_enrichment`).

## Fine-grained access control on analyst decisions
| kind | table | function | column |
|---|---|---|---|
| row filter | review_history | market_access | market |
| column mask | review_history | mask_reviewer | reviewer_email |

```sql
CREATE OR REPLACE FUNCTION market_access(market STRING) RETURNS BOOLEAN
RETURN current_user() = :data_owner OR is_account_group_member('admins')
    OR is_account_group_member(concat('northbeam_analysts_', lower(market)));
CREATE OR REPLACE FUNCTION mask_reviewer(reviewer_email STRING) RETURNS STRING
RETURN CASE WHEN current_user() = :data_owner OR is_account_group_member('admins') THEN reviewer_email
            ELSE concat('reviewer-', substr(sha2(reviewer_email, 256), 1, 8)) END;
```
A Spanish analyst (group `northbeam_analysts_es`) only sees ES decisions and sees reviewers as `reviewer-1a2b3c4d`.

## Tags (workspace enforces governed tag policies: `domain` must be an allowed value → `master_data`)
| object | tags |
|---|---|
| schema fe_bar_northbeam | domain=master_data, data_source=synthetic_and_public |
| gold_product_enrichment | layer=gold, classification=internal, serving=lakebase |
| review_history | layer=gold, classification=confidential; column reviewer_email: **pii=email** |
| silver_product_item | layer=silver, classification=internal |
| silver_public_reference | layer=silver, license=ODbL, origin=open_food_facts |
| run_metrics | layer=gold, classification=internal |

## Lineage captured by Unity Catalog (`system.access.table_lineage`)
| source | target | written by |
|---|---|---|
| bronze_delivery_es, bronze_delivery_us | silver_product_item | PIPELINE |
| bronze_delivery_es, bronze_delivery_us | silver_item_first_seen | PIPELINE |
| bronze_public_reference | silver_public_reference | PIPELINE |
| silver_public_reference | ref_embeddings | JOB |
| gold_product_enrichment | mv_enrichment_kpis | metric view |

Known gap: silver → gold lineage is not recorded because the resolution step MERGEs from a Python-built temp view
(see BUILD.md, decision 15).
