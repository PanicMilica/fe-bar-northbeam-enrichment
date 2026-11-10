# Unity Catalog evidence: governance, tags, lineage
_Collected 2026-11-10 17:42 UTC from workspace <workspace> (SQL warehouse 148ccb90800933a1)._

## Tables and comments

```sql
SELECT table_name, table_type, comment FROM milica_test.information_schema.tables
WHERE table_schema = 'fe_bar_northbeam' AND table_name NOT LIKE 'work_%' AND table_name NOT LIKE '__materialization%' ORDER BY table_name
```

| table_name | table_type | comment |
|---|---|---|
| __56298871_e815_4966_93c8_8b4d8403ca38_northbeam_public_gold_product_enrichment_3d2b8f27_056f_4d73_a0ae_d5f1af79f328 | MANAGED |  |
| bronze_delivery_es | STREAMING_TABLE | Raw weekly product deliveries for ES, exactly as received (Auto Loader). |
| bronze_delivery_us | STREAMING_TABLE | Raw weekly product deliveries for US, exactly as received (Auto Loader). |
| bronze_public_reference | STREAMING_TABLE | Public Open Food Facts snapshot of snack bars (ODbL), as downloaded. |
| evaluation_results | MANAGED |  |
| event_log_41577228_1dbb_4d95_b12f_77a559f39726 | MANAGED |  |
| event_log_56298871_e815_4966_93c8_8b4d8403ca38 | MANAGED |  |
| evidence | MANAGED | Every reference candidate considered per item (explainability / audit). |
| gold_product_enrichment | MANAGED | Enriched snack-bar attributes per retailer item. One row per market + item, persisted across deliveries. Synced to Lakebase for the review a |
| mv_enrichment_kpis | METRIC_VIEW | Enrichment KPIs for Northbeam: coverage, automation rate, review backlog, confidence and segment mix. |
| ref_embeddings | MANAGED | Embeddings of public reference product names (computed once, reused every run). |
| review_history | MANAGED | Analyst decisions from the review app (via Lakebase), applied to gold. Governed: row filter by market, reviewer masked. |
| run_metrics | MANAGED | One row per market per enrichment run: volumes, cost, runtime, review rate, analyst hours saved. |
| silver_item_first_seen | MATERIALIZED_VIEW | First and last delivery week per item; drives the 'new products only' worklist. |
| silver_product_item | STREAMING_TABLE | Standardised product master across markets: one row per market + item, latest delivery wins. |
| silver_public_reference | MATERIALIZED_VIEW | Cleaned public product reference: one row per GTIN with per-100 g and per-serving nutrition. |

## Table tags

```sql
SELECT table_name, tag_name, tag_value FROM milica_test.information_schema.table_tags
WHERE schema_name = 'fe_bar_northbeam' ORDER BY table_name, tag_name
```

| table_name | tag_name | tag_value |
|---|---|---|
| gold_product_enrichment | classification | internal |
| gold_product_enrichment | layer | gold |
| gold_product_enrichment | serving | lakebase |
| review_history | classification | confidential |
| review_history | layer | gold |
| run_metrics | classification | internal |
| run_metrics | layer | gold |
| silver_product_item | classification | internal |
| silver_product_item | layer | silver |
| silver_public_reference | layer | silver |
| silver_public_reference | license | ODbL |
| silver_public_reference | origin | open_food_facts |

## Column tags

```sql
SELECT table_name, column_name, tag_name, tag_value FROM milica_test.information_schema.column_tags
WHERE schema_name = 'fe_bar_northbeam' ORDER BY table_name
```

| table_name | column_name | tag_name | tag_value |
|---|---|---|---|
| review_history | reviewer_email | pii | email |

## Row filter and column mask on review_history

```sql
SELECT 'row_filter' AS kind, table_name, filter_name AS function_name, target_columns FROM milica_test.information_schema.row_filters WHERE table_schema = 'fe_bar_northbeam'
UNION ALL
SELECT 'column_mask', table_name, mask_name, column_name FROM milica_test.information_schema.column_masks WHERE table_schema = 'fe_bar_northbeam'
```

| kind | table_name | function_name | target_columns |
|---|---|---|---|
| row_filter | review_history | milica_test.fe_bar_northbeam.market_access | market |
| column_mask | review_history | milica_test.fe_bar_northbeam.mask_reviewer | reviewer_email |

## Governance functions

```sql
SELECT routine_name, comment FROM milica_test.information_schema.routines
WHERE routine_schema = 'fe_bar_northbeam' ORDER BY routine_name
```

| routine_name | comment |
|---|---|
| market_access | Row filter: data owner and admins see all markets; analysts only their market group (northbeam_analysts_es / _us). |
| mask_reviewer | Column mask: only the data owner sees reviewer e-mails; others see a stable pseudonym. |

## Lineage (system.access.table_lineage): how data flows between layers

```sql
SELECT DISTINCT source_table_name, target_table_name, entity_type
FROM system.access.table_lineage
WHERE (target_table_catalog = 'milica_test' AND target_table_schema = 'fe_bar_northbeam')
  AND source_table_name IS NOT NULL AND target_table_name IS NOT NULL
  AND target_table_name NOT LIKE 'work_%' AND event_date >= current_date() - INTERVAL 2 DAYS
ORDER BY target_table_name, source_table_name
```

| source_table_name | target_table_name | entity_type |
|---|---|---|
| gold_product_enrichment | mv_enrichment_kpis |  |
| ref_embeddings | ref_embeddings | JOB |
| silver_public_reference | ref_embeddings | JOB |
| bronze_delivery_es | silver_item_first_seen | PIPELINE |
| bronze_delivery_us | silver_item_first_seen | PIPELINE |
| silver_item_first_seen | silver_item_first_seen | PIPELINE |
| bronze_delivery_es | silver_product_item | PIPELINE |
| bronze_delivery_us | silver_product_item | PIPELINE |
| bronze_public_reference | silver_public_reference | PIPELINE |
