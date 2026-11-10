# Northbeam Retail Insights: AI product enrichment for snack-bar category insights

**Industry:** Consumer Goods / Retail measurement · **Buyer:** Chief Data & Product Officer (executive sponsor) and Head of Category Insights (domain owner)

> Northbeam is a fictional company; the scenario mirrors a real FE engagement pattern. All data is synthetic,
> built from the public [Open Food Facts](https://world.openfoodfacts.org) database (ODbL). No customer data.

## 1. The business problem

Northbeam harmonises weekly retailer product deliveries for FMCG snack brands and sells them category insights
("high-protein bars grew 12% in Spain"). Retailer files tell Northbeam *what* was sold, but not **calories and
protein per bar or the nutrition segment**, the attributes its brand clients actually pay for. Today analysts
research every new product by hand: about **6 minutes per product**, a **multi-week backlog**, and insight
reports that ship days after the data arrives. Private-label products (12% of items) have no barcode at all.

## 2. The outcome (measured on 3 weekly deliveries, 553 products, 2 markets)

| KPI the buyer cares about | Before (manual) | With this solution |
|---|---|---|
| Products enriched without an analyst | 0% | **63%** automatically, **100% precision** (every auto-enriched product correct vs. ground truth) |
| Wrong matches reaching client reports | depends on analyst | **0**: 100% of wrong AI matches were caught by the review queue |
| Time from delivery to enriched data | days to weeks | **~7 minutes** per weekly run (pipeline + enrichment + sync) |
| Cost per 1,000 products | ~100 analyst hours | **~$0.65** in model calls + a few minutes of serverless compute |
| Analyst hours saved (this sample) | | **34.5 h** across 3 deliveries; ≈ **3.3 FTE (~$215k) per year** at Northbeam scale (see [docs/VALUE.md](docs/VALUE.md)) |
| Explainability | analyst notes | every value has an evidence source, a 0-100 confidence score and a plain-English explanation |

Analysts no longer research products; they **review the 37% the AI is unsure about**, in a review app, and their
decisions are never overwritten by later runs. Results: [evidence/job_runs/2026W42_final_evaluation](evidence/job_runs/2026W42_final_evaluation/evaluate.md).

## 3. The end-to-end journey (one integrated loop, not separate demos)

```
 retailer CSVs (ES, US)          public Open Food Facts snapshot
        │ Auto Loader                     │ Auto Loader
        ▼                                 ▼
 ┌──────────────────────── LAKEFLOW DECLARATIVE PIPELINE ────────────────────────┐
 │ bronze_delivery_es/us ─▶ v_delivery_items (expectations) ─▶ AUTO CDC ─▶       │
 │                                         silver_product_item (1 row per item)  │
 │ bronze_public_reference ─▶ silver_public_reference (expect_or_drop quality)   │
 └───────────────────────────────────────────────────────────────────────────────┘
        │ UNITY CATALOG: comments, tags, row filter by market, masked reviewer, lineage
        ▼
 ┌──────────────────────── GEN AI ENRICHMENT (weekly job) ───────────────────────┐
 │ only NEW products ─▶ tier 1 exact barcode ─▶ tier 2 ai_translate + embeddings │
 │ (bge-large) top-3 ─▶ ai_query gpt-5.4-mini resolves the product (strict JSON)  │
 │ ─▶ gpt-5.4-nano judge ─▶ deterministic segment rules ─▶ confidence 0-100       │
 │ ─▶ MERGE gold_product_enrichment · MLflow evaluation vs. golden set           │
 └───────────────────────────────────────────────────────────────────────────────┘
        │ synced table (TRIGGERED)                       ▲ decisions applied to gold
        ▼                                                │ (human_verified, confidence 100)
 ┌──────── LAKEBASE (Postgres) ────────┐                 │
 │ public.gold_product_enrichment      │────────────────┐│
 │ review.review_decisions (app writes)│◀───────┐       ││
 └─────────────────────────────────────┘        │       ││
        ▼                                       │       ││
 ┌──────── DATABRICKS APP ─────────────┐  ┌─────┴───────┴┴─── GENIE AGENT ────────┐
 │ Overview · Review queue (approve /  │  │ "What is the high-protein share in    │
 │ correct / reject) · Ask Genie       │──│  Spain vs the US?" over gold +        │
 └─────────────────────────────────────┘  │  metric view mv_enrichment_kpis       │
                                          └───────────────────────────────────────┘
```

| Stage | What it does here | Code | Execution evidence (text) |
|---|---|---|---|
| **Lakeflow** | Auto Loader ingest of weekly deliveries + public reference, 8 expectations, AUTO CDC to one row per item | [src/pipeline/ingest.py](src/pipeline/ingest.py) | [evidence/lakeflow_pipeline.md](evidence/lakeflow_pipeline.md) |
| **Unity Catalog** | Comments on every table/column, tags, row filter by market, column mask on reviewer e-mail, lineage | [src/notebooks/00_setup_and_governance.sql](src/notebooks/00_setup_and_governance.sql) | [evidence/unity_catalog_governance.md](evidence/unity_catalog_governance.md) |
| **GenAI** | `ai_translate`, embeddings, `ai_query` resolution + LLM judge, rules, confidence, MLflow evaluation | [src/notebooks/01_enrich.py](src/notebooks/01_enrich.py), [03_evaluate.py](src/notebooks/03_evaluate.py) | [evidence/job_runs/](evidence/job_runs/) |
| **Lakebase** | Gold synced to Postgres for the app; app writes analyst decisions to Postgres; job applies them to gold | [src/notebooks/02_apply_reviews_and_sync.py](src/notebooks/02_apply_reviews_and_sync.py) | [evidence/lakebase_serving.md](evidence/lakebase_serving.md) |
| **Genie Agent** | Space over gold, silver, run metrics and the KPI metric view, with instructions and example SQL | [scripts/create_genie_space.py](scripts/create_genie_space.py) | [evidence/genie_answers.md](evidence/genie_answers.md) |
| **Databricks App** | Streamlit console: KPIs, review queue with evidence, Ask Genie | [app/app.py](app/app.py) | [evidence/app.md](evidence/app.md) |

Everything is one Declarative Automation Bundle ([databricks.yml](databricks.yml)): pipeline, job, app.

## 4. How the AI decides (and why it is trustworthy)

* **The LLM never invents numbers.** Nutrition comes from the matched public product; the LLM only decides
  *which* product a messy retailer line is ("BARR CER AVENA C/ CHOC NEGRO 25G 6UN") and qualitative positioning.
* **Cheap evidence first.** 76% of products resolve by exact barcode (free, deterministic). Only the rest go
  through translation, embeddings and the LLM.
* **Confidence is evidence-based, not self-reported.** Source tier × identity × judge × threshold margin ×
  completeness, capped at 95 unless a human verified it. The calibration table shows accuracy rising with the
  score (98-100% at ≥ 50, 48% below 30), so the review threshold (70) is meaningful.
* **Business owns the definitions.** Segment thresholds live in [config/attributes.yml](config/attributes.yml)
  (HIGH PROTEIN ≥ 15 g per bar, …), not in prompts; changing a definition re-segments only affected products.

## 5. Results by product type (golden set, final evaluation)

| Product type | Products | Correct match | Auto-enriched | Precision of auto-enriched |
|---|---|---|---|---|
| Branded, barcode in feed | 439 | 99.8% | 76% | 100% |
| Barcode missing | 36 | 75% | 14% | 100% |
| Private label, masked barcode | 58 | 64% | 9% | 100% |
| Private label, no public footprint | 20 | 60% correctly "no match" | 0% (all to review, as intended) | n/a |

Calibration (all products): confidence 90-100 → 98% correct · 70-89 → 100% · 50-69 → 99% · 30-49 → 79% · 0-29 → 48%.

## 6. Repository

```
config/            business definitions (segments) and per-market file mappings
src/pipeline/      Lakeflow declarative pipeline
src/notebooks/     00 governance · 01 enrich · 02 Lakebase loop + sync · 03 evaluation
src/enrichment_lib/ Spark-free logic (barcodes, evidence, rules, confidence, prompts), unit-tested
app/               Databricks App (Streamlit)
resources/         bundle resources: pipeline, weekly job, app
scripts/           data download + synthetic deliveries, Genie space, evidence collectors
data/              public reference snapshot, synthetic deliveries, golden labels (evaluation only)
evidence/          execution evidence as text (job runs with outputs, event logs, query results, Genie answers)
docs/              value case, decisions & trade-offs, AI usage, business deck
tests/             19 unit tests
```

More: [docs/VALUE.md](docs/VALUE.md) · [docs/DECISIONS.md](docs/DECISIONS.md) · [docs/AI_USAGE.md](docs/AI_USAGE.md) · [docs/DECK.md](docs/DECK.md) · [docs/RUNBOOK.md](docs/RUNBOOK.md)
