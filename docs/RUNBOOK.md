# Runbook: reproduce the build

Prerequisites: Databricks CLI ≥ 0.27x, a workspace with serverless, Lakebase, Databricks Apps, Genie and
Foundation Model APIs; Python 3.11+ locally.

```bash
# 0. Local tests
uv venv .venv && uv pip install --python .venv/bin/python pytest pyyaml psycopg[binary]
.venv/bin/python -m pytest -q tests                      # 19 passed

# 1. Data (public + synthetic). Already committed under data/; regenerate if you like:
python3 scripts/fetch_public_reference.py                # Open Food Facts snapshot (ODbL)
python3 scripts/generate_deliveries.py                   # ES + US, weeks 2026W40-W42 + golden labels

# 2. Workspace objects created once (CLI)
databricks schemas create fe_bar_northbeam milica_test -p dev
for v in landing public_reference golden; do databricks volumes create milica_test fe_bar_northbeam $v MANAGED -p dev; done
databricks fs cp -r data/public_reference dbfs:/Volumes/milica_test/fe_bar_northbeam/public_reference/ -p dev
databricks fs cp -r data/golden dbfs:/Volumes/milica_test/fe_bar_northbeam/golden/ -p dev
databricks database create-database-instance northbeam-enrichment --capacity CU_1 -p dev
databricks database create-database-catalog northbeam_lakebase northbeam-enrichment northbeam --create-database-if-not-exists -p dev

# 3. Deploy pipeline, job and app
databricks bundle deploy -p dev

# 4. Week by week: upload a delivery, run the job (file-arrival trigger is also defined, paused)
databricks fs cp -r data/landing/ES/2026W40 dbfs:/Volumes/milica_test/fe_bar_northbeam/landing/ES/2026W40 -p dev
databricks fs cp -r data/landing/US/2026W40 dbfs:/Volumes/milica_test/fe_bar_northbeam/landing/US/2026W40 -p dev
databricks bundle run northbeam_weekly_enrichment -p dev

# 5. Serving (once, after the first run created gold)
databricks database create-synced-database-table --json '{"name":"northbeam_lakebase.public.gold_product_enrichment",
  "spec":{"source_table_full_name":"milica_test.fe_bar_northbeam.gold_product_enrichment","primary_key_columns":["market","item_id"],
  "scheduling_policy":"TRIGGERED","new_pipeline_spec":{"storage_catalog":"milica_test","storage_schema":"fe_bar_northbeam"}}}' -p dev
#    Postgres: review.review_decisions + grants for the app service principal (see evidence/lakebase_serving.md)
python3 scripts/create_genie_space.py dev                # put the id in databricks.yml (genie_space_id)
databricks bundle deploy -p dev && databricks bundle run northbeam_review_app -p dev

# 6. Evidence (text, committed)
python3 scripts/export_run_evidence.py dev <job_run_id> <label>
python3 scripts/collect_platform_evidence.py dev <warehouse_id> <pipeline_id>
python3 scripts/ask_genie.py dev <space_id> evidence/genie_answers.md
.venv/bin/python scripts/collect_lakebase_evidence.py dev northbeam-enrichment
.venv/bin/python scripts/collect_app_evidence.py dev northbeam-enrichment-console northbeam-enrichment
```
