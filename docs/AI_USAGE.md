# How AI was used to build this (AI as a teammate)

## Tools
| Tool | Used for |
|---|---|
| **Claude Code** (CLI, Claude Opus) | Pair-programming the whole build: pipeline, notebooks, app, bundle, evidence collectors, docs. It ran the Databricks CLI against the workspace, read job outputs and fixed failures. |
| **Databricks CLI + Declarative Automation Bundles** | Deploying pipeline, job and app as code; running the weekly job; exporting run outputs as text evidence |
| **Databricks AI functions** (`ai_translate`, `ai_query`) | In the product itself: translation, product resolution, LLM judge |
| **Genie** | In the product itself: natural-language access; also used to sanity-check KPI numbers |

## How I worked with the assistant
1. **Started from my own earlier prototype** of this enrichment pattern (barcode normalisation, deterministic
   segment rules, evidence-based confidence), scrubbed of everything customer-specific, and asked Claude Code to
   extend it to the full FE Bar journey (Lakeflow, Lakebase, Genie, App).
2. **Decisions stayed mine**: fictional customer instead of the real one (public repo), public Open Food Facts data
   as the evidence source and golden set, "the LLM never writes numbers", review threshold, what goes to Lakebase.
3. **Evaluation-driven iteration**: every change was measured against the golden set. Two examples where the
   numbers changed the design:
   * first run: kcal error 46 kcal → traced to inconsistent per-serving values in public data and a mismatch
     between how the ground truth and the pipeline computed bar weight → per-bar values now always
     per-100 g × bar weight; implausible records dropped by a pipeline expectation → error 0.01 kcal.
   * first run: 50% of exact-barcode products went to review although they were 100% correct → the LLM judge
     now weighs 0.3 on exact barcodes and 1.0 on name matches → review rate 36%, precision still 100%.
4. **Platform constraints found and handled live**: governed tag policies in the workspace (tag values must be
   allowed), `CREATE WIDGET` not supported on SQL warehouses (switched to named parameters), stale embeddings
   after a data-quality rule removed reference rows.

## Prompt patterns used in the product ([src/enrichment_lib/prompts.py](../src/enrichment_lib/prompts.py))
* **Strict JSON schema** via `ai_query(..., responseFormat => ...)` with enums, so outputs are always parseable.
* **Candidates in, choice out**: the model picks one of the retrieved candidates or `null`; it cannot invent a product.
* **Calibrated wording** for identity: explicit bands ("exact barcode and consistent name: 0.95-1 …").
* **Separate, cheaper judge** that sees the product, the chosen match and the reasoning, and scores `same_product`.

## Conversation
Built in one Claude Code session (conversation ID available on request / in the submission form).
