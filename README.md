# Northbeam Retail Insights: AI product enrichment for snack-bar category insights

**Industry:** Consumer Goods / retail measurement (FMCG snack bars) · **Buyer:** Chief Data & Product Officer
(executive sponsor) and Head of Category Insights (domain owner) · Fictional company; all data synthetic or public
(Open Food Facts, ODbL). No customer data.

## The business problem
Northbeam harmonises weekly retailer product deliveries for FMCG snack brands and sells them category insights such
as *"high-protein bars grew 12% in Spain"*. Retailer files say **what** sold, but not **calories and protein per bar or
the nutrition segment**, the attributes brand clients pay for. Analysts research each new product by hand (~6 minutes,
~120 hours a week), so there is a backlog, reports ship days late, and private label (12% of items, no barcode) is
rarely enriched.

## The outcome (measured: 3 weekly deliveries, 553 products, Spain + US)
| KPI | Manual today | With this solution |
|---|---|---|
| Products enriched with no analyst touch | 0% | **63%** |
| Precision of auto-enriched products | n/a | **100%** vs. ground truth (protein within 1 g: 99.7%) |
| Wrong AI matches reaching client data | n/a | **0**: 100% caught by the review queue |
| Delivery → enriched data | days to weeks | **~7 minutes** per weekly run |
| Model cost per 1,000 products | ~100 analyst hours | **~$0.65** |
| At Northbeam scale (assumptions in BUILD.md) | 120 analyst h / week | **105 h / week saved ≈ 3.3 FTE ≈ $215k / year**, plus ~$300k ARR potential |

Analysts stop researching and only **review the 37% the AI is unsure about** in a Databricks App. Their decisions
are final, and every value has a source, a 0-100 confidence score and a plain-English explanation.

## One integrated journey: raw data → Lakeflow → Unity Catalog → GenAI → Lakebase → Genie → App
```
retailer CSVs (ES/US, weekly) + public product snapshot
  └─▶ LAKEFLOW pipeline: Auto Loader bronze → expectations → AUTO CDC silver_product_item
       └─▶ UNITY CATALOG: one governed schema, comments, tags, row filter, column mask, lineage
            └─▶ GENAI (weekly job, only NEW products): exact barcode → ai_translate + embeddings top-3
                 → ai_query gpt-5.4-mini resolves product (strict JSON) → gpt-5.4-nano judge
                 → business rules → confidence → gold_product_enrichment → MLflow evaluation
                 └─▶ LAKEBASE: gold synced to Postgres; app writes analyst decisions to Postgres
                      └─▶ DATABRICKS APP (review queue, KPIs, Ask Genie) ──decisions──▶ job applies them to gold
                      └─▶ GENIE AGENT over gold + KPI metric view: "high-protein share Spain vs US?" → 25.5% vs 24.9%
```

| Stage | Code | Execution evidence (text) |
|---|---|---|
| Lakeflow | `src/pipeline/ingest.py` | `evidence/01_lakeflow_ingest_pipeline_results.md` |
| Unity Catalog | `src/gold/00_gold_governance.sql` | `evidence/02_unity_catalog_governance_results.md` |
| GenAI enrichment | `src/gold/01_gold_genai_enrichment.py`, `src/enrichment_lib/` | `evidence/03_gold_genai_enrichment_run_logs.md` |
| Evaluation (MLflow) | `src/eval/03_model_eval.py` | `evidence/04_model_eval_results_metrics.md`, `evidence/05_gold_product_enrichment_results.md` |
| Lakebase | `src/lakebase/02_lakebase_sync_reviews.py` | `evidence/06_lakebase_sync_and_review_loop_results.md` |
| Genie Agent | `scripts/genie_agent_space.py` | `evidence/07_genie_agent_answers_results.md` |
| Databricks App | `lakebase_app/app.py` | `evidence/08_lakebase_app_results.md` |

Everything is one Declarative Automation Bundle (`databricks.yml`, `resources/`): pipeline, weekly job (5 tasks,
file-arrival trigger), app. Architecture, decisions, value model and AI usage: **[BUILD.md](BUILD.md)**.
Business deck: `docs/DECK.md`. Reproduce: `docs/RUNBOOK.md`.

## Why it is trustworthy
* **The LLM never writes numbers**: nutrition comes from the matched public product; the LLM only decides *which*
  product a messy line like `BARR CER AVENA C/ CHOC NEGRO 25G 5UN` is, and its qualitative positioning.
* **Cheap evidence first**: 76% resolve by exact barcode at zero model cost.
* **Calibrated confidence**: 98-100% correct at confidence ≥ 50, 48% below 30; the 70 threshold routes the right products to people.
* **Business owns the definitions**: segment thresholds (HIGH PROTEIN ≥ 15 g per bar …) live in `config/attributes.yml`, not in prompts.
