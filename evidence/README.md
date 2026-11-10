# Execution evidence (text)

Everything here was produced by running the build in a Databricks workspace (Azure) on 2026-11-10,
then exported as text so it can be read without screenshots.

| File | What it proves |
|---|---|
| [job_runs/](job_runs/) | The weekly job's notebooks **with their real cell outputs**, one folder per delivery week (W40 initial, W41 with analyst decisions applied, W42 incremental, final evaluation) |
| [lakeflow_pipeline.md](lakeflow_pipeline.md) | Lakeflow event log: updates, rows per flow, data-quality expectations passed/failed |
| [unity_catalog_governance.md](unity_catalog_governance.md) | Comments, tags, row filter, column mask, governance functions, lineage from `system.access` |
| [gold_results.md](gold_results.md) | KPIs from the metric view, segment mix, samples (auto, name-matched, review), human-verified rows, run metrics, evaluation history |
| [lakebase_serving.md](lakebase_serving.md) | Synced table state, rows in Postgres, decisions written by the app, point-lookup latency, grants |
| [genie_answers.md](genie_answers.md) | Six questions answered by the Genie space: generated SQL + result rows + answer text |
| [app.md](app.md) | App deployment status, bound resources and the exact queries the app runs, executed against Lakebase |

Masked for a public repo: workspace and app URLs, Lakebase host, the app's service principal id, and the
analyst's e-mail (shown as `analyst@northbeam.example`). No customer data: deliveries are synthetic and the
product reference is public Open Food Facts data (ODbL).
