# BUILD: how the Northbeam enrichment works, why it is built this way, and what it is worth

## 1. Stage by stage (all deployed by one bundle, run weekly by job `northbeam_weekly_enrichment`)
| # | Stage | What happens | Key objects |
|---|---|---|---|
| 1 | **Lakeflow** (`src/pipeline/ingest.py`) | Auto Loader reads each new weekly CSV per market (Spanish and US formats differ, mapped by `config/markets.yml`); barcodes normalised (US feed drops the GTIN check digit, restored); 4 expectations on deliveries and 3 on the public reference; **AUTO CDC** keeps one row per market + item. | `bronze_delivery_es/us`, `v_delivery_items`, `silver_product_item`, `silver_item_first_seen`, `silver_public_reference` |
| 2 | **Unity Catalog** (`src/gold/00_gold_governance.sql`) | One governed schema; comments on tables and columns; tags under the workspace's governed tag policies; **row filter by market** and **column mask on reviewer e-mail** (tag `pii=email`) on analyst decisions; Lakebase registered as UC catalog; lineage in `system.access`. | `market_access()`, `mask_reviewer()`, `mv_enrichment_kpis` (metric view) |
| 3 | **GenAI** (`src/gold/01_gold_genai_enrichment.py`) | Worklist = products never enriched under the current definitions version. Tier 1 exact barcode join. Tier 2: `ai_translate` (ES → EN), `databricks-bge-large-en` embeddings, cosine top-3 candidates. `ai_query` **gpt-5.4-mini** with a strict JSON schema chooses the candidate (or none), positioning and hero ingredient; **gpt-5.4-nano** judges the match. Deterministic rules set the segment; an evidence-based score sets confidence; MERGE into gold (human-verified rows untouched). | `gold_product_enrichment`, `evidence`, `ref_embeddings`, `run_metrics` |
| 4 | **Evaluation** (`src/eval/03_model_eval.py`) | Golden set from the generator (true product + true nutrition per item): automation rate, precision of auto rows, calibration per confidence bucket, cost, logged to MLflow every week. | `evaluation_results`, MLflow experiment |
| 5 | **Lakebase** (`src/lakebase/02_lakebase_sync_reviews.py`) | Gold → Postgres via a **synced table** (TRIGGERED, refreshed by the job). The app writes decisions to `review.review_decisions`; the job copies them to `review_history`, applies them to gold (`human_verified`, confidence 100) and re-syncs. | instance `northbeam-enrichment` (CU_1), catalog `northbeam_lakebase` |
| 6 | **Genie Agent** (`scripts/genie_agent_space.py`) | Space over gold, silver, run metrics and the KPI metric view, with business instructions (segment definitions, status meanings) and example SQL. | space "Northbeam · Snack Bar Product Intelligence" |
| 7 | **Databricks App** (`lakebase_app/app.py`) | Streamlit console: Overview KPIs from Lakebase; Review queue with evidence and approve / correct / reject; Ask Genie (Conversation API). Runs as its own service principal with SELECT on gold and INSERT on decisions only. | app `northbeam-enrichment-console` |

Data: `scripts/fetch_public_reference.py` downloads 1,160 real snack bars from Open Food Facts (public, ODbL);
`scripts/generate_deliveries.py` turns them into 3 weekly retailer deliveries per market with realistic quirks
(abbreviated Spanish descriptors, US 11-digit codes, 12% private label with masked barcode, missing barcodes, and 20
store-brand products with no public footprint), and writes the golden labels used only for evaluation.

## 2. Confidence score (`src/enrichment_lib/confidence.py`)
`score = 100 × source tier × identity match × agreement × threshold margin × completeness × judge × fallback`, capped
at 95; only a human gets 100. Source tier: exact barcode 0.90, name match 0.75, none 0.35. The judge weighs 0.3 on
exact barcodes and 1.0 on name matches. A value within 10% of a segment threshold gets 0.75 (borderline). Below 70 →
review. Calibration on the golden set: 90-100 → 98% correct (the only misses are analyst-edited rows), 70-89 → 100%,
50-69 → 99%, 30-49 → 79%, 0-29 → 48%.

## 3. Decisions and trade-offs
| Decision | Alternative | Why | Cost |
|---|---|---|---|
| Deterministic workflow with LLM steps | Autonomous multi-agent loop | Batch enrichment is a fixed sequence: cheaper, testable, every step is a table | Less open-ended (Genie covers questions) |
| LLM resolves identity, **numbers come from data** | LLM extracts nutrition | A wrong number in a client report is the worst failure; kcal error is 0.01 when matched | No numbers without a match → review |
| Cheap evidence first (barcode, then AI) | LLM for everything | 76% free and deterministic; model spend only on the hard 24% | Two code paths |
| Embeddings + in-memory top-3 | Mosaic AI Vector Search | ~1,100 reference products: an index adds cost and no accuracy | Switch to Vector Search above ~100k |
| Two models: mini resolves, nano judges | Same model twice / bigger model | An independent, cheaper auditor catches errors the first model misses (example: ES-100074, judge 0 → review) | Two endpoints |
| Rules in YAML owned by the business | Definitions inside prompts | Analysts change "≥ 15 g" without touching prompts; versioning re-segments only affected products | LLM still needed for positioning |
| Incremental enrichment + AUTO CDC | Re-process every delivery | W41 enriched 38 and W42 55 products, not 500 | Definition change = catch-up run |
| Lakebase for the app | App on the SQL warehouse / writes to Delta | Millisecond point reads and transactional multi-user writes; Delta stays the source of truth | Second copy of gold, refreshed by the job |
| Row filter + mask on `review_history`, not on gold | Filter gold too | Keeps the sync and Genie path simple; access to gold controlled by UC grants | Gold readable by anyone with schema SELECT |
| Human decisions final | Re-score every run | Analyst trust; best calibration signal | Undoing needs a new decision |
| Public products + synthetic quirks + golden set | Hand-made fake data | Real evidence and an objective ground truth for precision | Retailer quirks are simulated |
| Known gap: silver → gold lineage | Rewrite resolution in SQL | Prompts are built in Python and MERGEd from a temp view, so UC lineage stops at silver/embeddings | Next step: candidates to Delta + `ai_query` in SQL |

## 4. Value model (measured + stated assumptions)
Measured: 63% automation, 100% auto precision, $0.64-0.66 per 1,000 products in model calls, ~7 min per weekly run
(ingest 2.3, enrich 2.2, sync 1.5, evaluate 1.1 min).
Assumptions (replace with the customer's): 1,200 new products / week (8 markets), 6 min manual research, 2 min
review with evidence shown, 1,650 productive h / year, $65k loaded analyst cost, 40,000-item backlog per new category,
15 brand clients × $20k for a "functional nutrition" report.

| | Manual | With the solution | Impact |
|---|---|---|---|
| Analyst time / week | 120 h (≈ 3.8 FTE) | 1,200 × 37% × 2 min = 15 h | **105 h saved ≈ 3.3 FTE ≈ $215k / year** |
| New 40,000-item category | 4,000 h | ~$26 of model calls + 490 h review | **~88% less effort** |
| Delivery → enriched | days-weeks | same day | reports ship with the delivery |
| New revenue | limited by backlog | every product has attributes | **~$300k ARR** potential |
| Run cost | | tokens ~$40 / yr; jobs + Lakebase CU_1 + app est. $5-8k / yr (list price, to confirm in `system.billing`) | |

Executive sponsor: ~$0.5M a year of savings and new revenue for single-digit thousands of platform cost.
Domain owner: analysts review instead of research, every number has a source, definitions are theirs.

## 5. How AI was used to build it
* **Claude Code** pair-programmed the build: pipeline, notebooks, app, bundle, evidence exporters, docs; it ran the
  Databricks CLI, read job outputs and fixed failures. Starting point: my own earlier prototype of this pattern
  (barcode normalisation, rules, confidence), scrubbed of anything customer-specific.
* **Decisions stayed mine**: fictional customer + public data, "the LLM never writes numbers", review threshold,
  Lakebase for the app, evaluation-driven iteration.
* **Evaluation changed the design** (all measured on the golden set):
  1. kcal error 46 → 0.01: per-bar = per-100 g × bar weight, implausible public records dropped by an expectation.
  2. 50% of correct exact-barcode products went to review → judge weight per evidence tier → review 36%, precision still 100%.
  3. Correct non-bar products (cookies) went to review → `NOT A SNACK BAR` label → automation 63%.
* **Platform constraints handled live**: governed tag policies (allowed values only), no `CREATE WIDGET` on SQL
  warehouses (named parameters instead), stale embeddings after a data-quality rule removed reference rows.
* **Prompt patterns** (`src/enrichment_lib/prompts.py`): strict JSON schema with enums via `ai_query(responseFormat)`;
  "candidates in, one choice or null out" so the model cannot invent a product; explicit identity bands; a separate,
  cheaper judge.

## 6. Next steps with the customer
1. 200 analyst-labelled products per market → recalibrate weights and the 70 threshold on their data.
2. More private-label evidence: retailer web pages via a UC HTTP connection, `ai_parse_document` on pack images.
3. Enable the file-arrival trigger (defined, paused in the demo) on their landing zone.
4. Expose the resolve step as a UC function / MCP tool for Northbeam's internal assistant.
