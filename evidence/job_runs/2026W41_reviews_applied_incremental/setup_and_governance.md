# setup_and_governance · task run 747388460692259 · SUCCESS

Notebook: `af873f7c-d92d-4de7-aba6-83c3780d58d1` (language: sql)

# 00 · Setup and Unity Catalog governance
Idempotent: creates the gold / serving tables and applies governance on every run.
* **Comments and tags** on every table so Genie, the app and auditors understand the data.
* **Row filter by market** on review history: a market analyst only sees their market's decisions.
* **Column mask** on reviewer e-mail: only the data owner sees who reviewed what.
* Primary key + change data feed on gold, so it can be synced to Lakebase.


```sql
-- Parameters (job base_parameters): :catalog, :schema, :data_owner
SELECT :catalog AS catalog, :schema AS schema, :data_owner AS data_owner;
```
**Output:**
| catalog | schema | data_owner |
|---|---|---|
| milica_test | fe_bar_northbeam | analyst@northbeam.example |

```sql
USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

CREATE TABLE IF NOT EXISTS gold_product_enrichment (
  market STRING NOT NULL COMMENT 'Market code (ES, US)',
  item_id STRING NOT NULL COMMENT 'Retailer item id from the delivery',
  gtin13 STRING COMMENT 'Normalised barcode from the delivery (null for private label / missing)',
  descriptor STRING COMMENT 'Retailer descriptor as delivered',
  descriptor_en STRING COMMENT 'Descriptor translated to English (ai_translate)',
  brand STRING,
  is_private_label BOOLEAN,
  matched_gtin13 STRING COMMENT 'Public reference product resolved as the same product',
  matched_product_name STRING,
  kcal_per_bar DOUBLE COMMENT 'Energy per bar (kcal), from the matched public reference',
  protein_g_per_bar DOUBLE COMMENT 'Protein per bar (g), from the matched public reference',
  segment STRING COMMENT 'Snack-bar segment from deterministic rules in config/attributes.yml',
  sub_segment STRING,
  claimed_ingredient STRING COMMENT 'Hero ingredient (LLM, from name + ingredients)',
  positioning STRING COMMENT 'diet / fruit_nut / indulgent / wholesome (LLM)',
  confidence_score INT COMMENT '0-100 evidence-based confidence; 100 only when human verified',
  confidence_factors STRING COMMENT 'JSON breakdown of the confidence score',
  evidence_tier STRING COMMENT 'barcode_exact / name_match / none',
  explanation STRING COMMENT 'Human-readable reason for the values, with source',
  needs_review BOOLEAN COMMENT 'Below the review threshold or no evidence',
  human_verified BOOLEAN COMMENT 'Corrected or approved by an analyst in the review app',
  reviewed_by STRING,
  definitions_version INT COMMENT 'Version of config/attributes.yml used',
  first_enriched_week STRING COMMENT 'Delivery week the product was first enriched',
  model_resolve STRING, model_judge STRING,
  updated_at TIMESTAMP,
  CONSTRAINT pk_gold_product_enrichment PRIMARY KEY (market, item_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true)
COMMENT 'Enriched snack-bar attributes per retailer item. One row per market + item, persisted across deliveries. Synced to Lakebase for the review app.';

CREATE TABLE IF NOT EXISTS evidence (
  market STRING, item_id STRING, delivery_week STRING, candidate_rank INT, match_type STRING,
  candidate_gtin13 STRING, candidate_name STRING, similarity DOUBLE, chosen BOOLEAN, created_at TIMESTAMP
) COMMENT 'Every reference candidate considered per item (explainability / audit).';

CREATE TABLE IF NOT EXISTS ref_embeddings (
  gtin13 STRING, search_name STRING, embedding ARRAY<FLOAT>, model STRING, created_at TIMESTAMP
) COMMENT 'Embeddings of public reference product names (computed once, reused every run).';

CREATE TABLE IF NOT EXISTS run_metrics (
  run_id STRING, delivery_week STRING, market STRING, products INT, barcode_exact INT, name_match INT,
  no_evidence INT, llm_calls INT, est_cost_usd DOUBLE, cost_per_1000_usd DOUBLE, runtime_s DOUBLE,
  avg_confidence DOUBLE, review_rate DOUBLE, analyst_hours_saved DOUBLE, created_at TIMESTAMP
) COMMENT 'One row per market per enrichment run: volumes, cost, runtime, review rate, analyst hours saved.';

CREATE TABLE IF NOT EXISTS review_history (
  market STRING, item_id STRING, action STRING, field STRING, ai_value STRING, corrected_value STRING,
  comment STRING, reviewer_email STRING, reviewed_at TIMESTAMP, applied_at TIMESTAMP
) COMMENT 'Analyst decisions from the review app (via Lakebase), applied to gold. Governed: row filter by market, reviewer masked.';
```
**Output:**
|  |
|
|  |
|
|  |
|
|  |
|
|  |
|
|  |
|
|  |
|

## Governance: row filter + column mask


```sql
CREATE OR REPLACE FUNCTION market_access(market STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: data owner and admins see all markets; analysts only their market group (northbeam_analysts_es / _us).'
RETURN current_user() = :data_owner
    OR is_account_group_member('admins')
    OR is_account_group_member(concat('northbeam_analysts_', lower(market)));

CREATE OR REPLACE FUNCTION mask_reviewer(reviewer_email STRING)
RETURNS STRING
COMMENT 'Column mask: only the data owner sees reviewer e-mails; others see a stable pseudonym.'
RETURN CASE WHEN current_user() = :data_owner OR is_account_group_member('admins') THEN reviewer_email
            ELSE concat('reviewer-', substr(sha2(reviewer_email, 256), 1, 8)) END;

ALTER TABLE review_history SET ROW FILTER market_access ON (market);
ALTER TABLE review_history ALTER COLUMN reviewer_email SET MASK mask_reviewer;
```
**Output:**
|  |
|
|  |
|
|  |
|
|  |
|

## Tags (classification + domain)


```sql
ALTER SCHEMA IDENTIFIER(:schema) SET TAGS ('domain' = 'master_data', 'data_source' = 'synthetic_and_public');
ALTER TABLE gold_product_enrichment SET TAGS ('layer' = 'gold', 'classification' = 'internal', 'serving' = 'lakebase');
ALTER TABLE review_history SET TAGS ('layer' = 'gold', 'classification' = 'confidential');
ALTER TABLE review_history ALTER COLUMN reviewer_email SET TAGS ('pii' = 'email');
ALTER TABLE silver_public_reference SET TAGS ('layer' = 'silver', 'license' = 'ODbL', 'origin' = 'open_food_facts');
ALTER TABLE silver_product_item SET TAGS ('layer' = 'silver', 'classification' = 'internal');
ALTER TABLE run_metrics SET TAGS ('layer' = 'gold', 'classification' = 'internal');
```
**Output:**
|  |
|
|  |
|
|  |
|
|  |
|
|  |
|
|  |
|
|  |
|

```sql
SELECT table_name, comment FROM information_schema.tables
WHERE table_schema = :schema ORDER BY table_name;
```
**Output:**
| table_name | comment |
|---|---|
| __56298871_e815_4966_93c8_8b4d8403ca38_northbeam_public_gold_product_enrichment_3d2b8f27_056f_4d73_a0ae_d5f1af79f328 |  |
| __materialization_mat_41577228_1dbb_4d95_b12f_77a559f39726_bronze_delivery_es_1 | Raw weekly product deliveries for ES, exactly as received (Auto Loader). |
| __materialization_mat_41577228_1dbb_4d95_b12f_77a559f39726_bronze_delivery_us_1 | Raw weekly product deliveries for US, exactly as received (Auto Loader). |
| __materialization_mat_41577228_1dbb_4d95_b12f_77a559f39726_bronze_public_reference_1 | Public Open Food Facts snapshot of snack bars (ODbL), as downloaded. |
| __materialization_mat_41577228_1dbb_4d95_b12f_77a559f39726_silver_item_first_seen_1 | First and last delivery week per item; drives the 'new products only' worklist. |
| __materialization_mat_41577228_1dbb_4d95_b12f_77a559f39726_silver_product_item_1 | Standardised product master across markets: one row per market + item, latest delivery wins. |
| __materialization_mat_41577228_1dbb_4d95_b12f_77a559f39726_silver_public_reference_1 | Cleaned public product reference: one row per GTIN with per-100 g and per-serving nutrition. |
| bronze_delivery_es | Raw weekly product deliveries for ES, exactly as received (Auto Loader). |
| bronze_delivery_us | Raw weekly product deliveries for US, exactly as received (Auto Loader). |
| bronze_public_reference | Public Open Food Facts snapshot of snack bars (ODbL), as downloaded. |
| evaluation_results |  |
| event_log_41577228_1dbb_4d95_b12f_77a559f39726 |  |
| event_log_56298871_e815_4966_93c8_8b4d8403ca38 |  |
| evidence | Every reference candidate considered per item (explainability / audit). |
| gold_product_enrichment | Enriched snack-bar attributes per retailer item. One row per market + item, persisted across deliveries. Synced to Lakeb |
| mv_enrichment_kpis | Enrichment KPIs for Northbeam: coverage, automation rate, review backlog, confidence and segment mix. |
| ref_embeddings | Embeddings of public reference product names (computed once, reused every run). |
| review_history | Analyst decisions from the review app (via Lakebase), applied to gold. Governed: row filter by market, reviewer masked. |
| run_metrics | One row per market per enrichment run: volumes, cost, runtime, review rate, analyst hours saved. |
| silver_item_first_seen | First and last delivery week per item; drives the 'new products only' worklist. |
| silver_product_item | Standardised product master across markets: one row per market + item, latest delivery wins. |
| silver_public_reference | Cleaned public product reference: one row per GTIN with per-100 g and per-serving nutrition. |
| work_items |  |
| work_judged |  |
| work_resolved |  |

## Metric view: the business KPIs (used by Genie and the app)


```sql
CREATE OR REPLACE VIEW mv_enrichment_kpis
WITH METRICS
LANGUAGE YAML
COMMENT 'Enrichment KPIs for Northbeam: coverage, automation rate, review backlog, confidence and segment mix.'
AS $$
version: 0.1
source: gold_product_enrichment
dimensions:
  - name: market
    expr: market
  - name: segment
    expr: coalesce(segment, 'UNRESOLVED')
  - name: evidence_tier
    expr: evidence_tier
  - name: first_enriched_week
    expr: first_enriched_week
  - name: is_private_label
    expr: is_private_label
  - name: status
    expr: CASE WHEN human_verified THEN 'human verified' WHEN needs_review THEN 'needs review' ELSE 'auto-enriched' END
measures:
  - name: products
    expr: count(1)
  - name: auto_enriched_products
    expr: count(1) FILTER (WHERE NOT needs_review AND NOT human_verified)
  - name: products_needing_review
    expr: count(1) FILTER (WHERE needs_review AND NOT human_verified)
  - name: human_verified_products
    expr: count(1) FILTER (WHERE human_verified)
  - name: automation_rate
    expr: count(1) FILTER (WHERE NOT needs_review) / count(1)
  - name: attribute_coverage
    expr: count(1) FILTER (WHERE protein_g_per_bar IS NOT NULL AND kcal_per_bar IS NOT NULL) / count(1)
  - name: avg_confidence
    expr: avg(confidence_score)
  - name: high_protein_share
    expr: count(1) FILTER (WHERE segment = 'HIGH PROTEIN') / count(1) FILTER (WHERE segment IS NOT NULL AND segment <> 'NOT A SNACK BAR')
$$;
```
**Output:**
| result |
|---|