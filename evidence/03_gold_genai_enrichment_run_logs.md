# Evidence 3 · GenAI enrichment runs, week by week (executed)
Notebook: [src/gold/01_gold_genai_enrichment.py](../src/gold/01_gold_genai_enrichment.py), job task `enrich` (serverless).
Models: `ai_translate` · embeddings `databricks-bge-large-en` · resolve `databricks-gpt-5-4-mini` (ai_query, strict JSON) ·
judge `databricks-gpt-5-4-nano`. Below: the notebook's real printed outputs, copied from the exported job runs.

## Week 2026W40: first delivery, 460 products (job run 595905184235304)
```text
worklist: 460 new products            (ES 2026W40: 230, US 2026W40: 230)
tier 1 exact barcode matches: 352
tier 2 name matching for 108 products against 1155 reference products
resolved 460 products, 0 LLM errors
notebook exit value: {"products": 460, "runtime_s": 143.0}
```
| market | products | barcode_exact | name_match | no_evidence | llm_calls | est_cost_usd | cost_per_1000_usd | runtime_s | avg_confidence | review_rate | analyst_hours_saved |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ES | 230 | 178 | 38 | 14 | 460 | 0.1502 | 0.65 | 143.0 | 68.2 | 0.374 | 14.4 |
| US | 230 | 174 | 48 | 8 | 460 | 0.1502 | 0.65 | 143.0 | 70.9 | 0.361 | 14.7 |

## Week 2026W41: incremental, only new products (job run 843351037895198)
```text
worklist: 38 new products             (ES 2026W41: 18, US 2026W41: 20)
tier 1 exact barcode matches: 27
tier 2 name matching for 11 products against 1155 reference products
resolved 38 products, 0 LLM errors
notebook exit value: {"products": 38, "runtime_s": 87.5}
```
| market | products | barcode_exact | name_match | no_evidence | cost_per_1000_usd | avg_confidence | review_rate | analyst_hours_saved |
|---|---|---|---|---|---|---|---|---|
| ES | 18 | 13 | 4 | 1 | 0.66 | 65.6 | 0.50 | 0.9 |
| US | 20 | 14 | 6 | 0 | 0.66 | 68.2 | 0.45 | 1.1 |

## Week 2026W42: incremental (job run 68227308960061)
```text
worklist: 55 new products             (ES 2026W42: 23, US 2026W42: 32)
tier 1 exact barcode matches: 43
tier 2 name matching for 12 products against 1155 reference products
resolved 55 products, 0 LLM errors
notebook exit value: {"products": 55, "runtime_s": 85.7}
```
| market | products | barcode_exact | name_match | no_evidence | cost_per_1000_usd | avg_confidence | review_rate | analyst_hours_saved |
|---|---|---|---|---|---|---|---|---|
| ES | 23 | 18 | 3 | 2 | 0.64 | 70.5 | 0.348 | 1.5 |
| US | 32 | 25 | 7 | 0 | 0.64 | 71.5 | 0.406 | 1.9 |

## Re-run with no new delivery (job run 995564116033501, after renaming files)
```text
notebook exit value: {"products": 0}      (worklist empty: the notebook exits before any model call)
```
Nothing is paid for twice: products already enriched under the current definitions version are skipped.

## Totals over the three deliveries
553 products · 422 exact barcode (76%) · 106 name match · 25 no evidence · 1,106 LLM calls, 0 errors ·
est. model cost $0.36 in total ($0.64-0.66 per 1,000 products) · 34.5 analyst hours saved.
