# Value case: Northbeam Retail Insights

Two numbers are **measured** in this build (automation rate, precision, cost per 1,000 products, runtime).
Everything about Northbeam's scale is an **assumption**, stated so the buyer can replace it with their own.

## Measured on the build (3 weekly deliveries, 553 products, ES + US)

| Metric | Value | Source |
|---|---|---|
| Automation rate (no analyst touch) | 63% | [evaluate.md](../evidence/job_runs/2026W42_final_evaluation/evaluate.md) |
| Precision of auto-enriched products | 100% (protein within 1 g: 99.7%) | same |
| Wrong AI matches caught by review | 100% | same |
| Model cost per 1,000 products | $0.64-0.66 (token-based estimate at list price) | [gold_results.md](../evidence/gold_results.md) run metrics |
| Weekly run, end to end | ~7 minutes (ingest 2.3, enrich 2.2, Lakebase sync 1.5, evaluate 1.1) | [job run](../evidence/job_runs/2026W42_incremental/README.md) |

## Assumptions for Northbeam (replace with the customer's numbers)

| Assumption | Value | Why it is reasonable |
|---|---|---|
| New products per week, all markets and clients | 1,200 | 8 markets × ~150 new or changed snack / confectionery items per weekly delivery |
| Manual research per product | 6 minutes | find the product online, read the nutrition panel, convert per 100 g to per bar, classify |
| Analyst review per flagged product (with evidence shown) | 2 minutes | the app shows the candidate, numbers and reason; the analyst confirms or corrects |
| Productive analyst hours per year | 1,650 | |
| Loaded analyst cost | $65,000 / year | |
| Backlog when a new category is onboarded | 40,000 items | |
| New "functional nutrition" report sold to brand clients | 15 clients × $20,000 / year | attribute-based segments (high protein, low calorie) are a premium insight |

## Business impact

| | Manual today | With the solution | Impact |
|---|---|---|---|
| Analyst hours per week on enrichment | 1,200 × 6 min = **120 h** (≈ 3.8 FTE) | 1,200 × 37% × 2 min = **15 h** | **105 h / week saved ≈ 3.3 FTE ≈ $215k / year** |
| Onboarding a 40,000-item category | 4,000 h (≈ 2.4 FTE-years) | ~$26 in model calls + 490 h of review | **~88% less effort, weeks instead of a year** |
| Time from delivery to enriched data | days to weeks (backlog) | same day (~7 min job) | insight reports ship **with** the delivery |
| New revenue | segment reports limited by backlog | attributes available for every product | **~$300k ARR** potential (assumption) |
| Run cost | | tokens: ~$40 / year; serverless job + Lakebase CU_1 + app: **est. $5-8k / year** at list price | to confirm with `system.billing` after a month |

**For the executive sponsor (Chief Data & Product Officer):** roughly **$0.5M per year** of combined savings and
new revenue for single-digit thousands of platform cost, with no new headcount for category expansion.

**For the domain owner (Head of Category Insights):** analysts stop doing copy-paste research and only review what
the AI is unsure about; every number has a source and an explanation; segment definitions are theirs to change.
