"""Collect platform evidence as text: Lakeflow event log + data quality, Unity Catalog governance
and lineage, Lakebase state, gold samples. Writes evidence/*.md.

Usage: python scripts/collect_platform_evidence.py <profile> <warehouse_id> <pipeline_id>
"""
import json, subprocess, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

PROFILE, WH, PIPELINE = sys.argv[1], sys.argv[2], sys.argv[3]
CS = "milica_test.fe_bar_northbeam"
OUT = Path(__file__).resolve().parents[1] / "evidence"


def sql(statement):
    body = {"statement": statement, "warehouse_id": WH, "wait_timeout": "50s", "format": "JSON_ARRAY", "disposition": "INLINE"}
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "-p", PROFILE, "--json", json.dumps(body)],
                                  capture_output=True, text=True).stdout)
    while r.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        time.sleep(3)
        r = json.loads(subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", "-p", PROFILE],
                                      capture_output=True, text=True).stdout)
    if r.get("status", {}).get("state") != "SUCCEEDED":
        return f"_query failed: {r.get('status')}_"
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    rows = r.get("result", {}).get("data_array", []) or []
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join("" if v is None else str(v).replace("|", "/").replace("\n", " ")[:140] for v in row) + " |" for row in rows]
    return "\n".join(lines)


def section(title, statement, note=""):
    return f"## {title}\n{note}\n```sql\n{statement.strip()}\n```\n\n{sql(statement)}\n"


stamp = f"_Collected {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} from workspace <workspace> (SQL warehouse {WH})._\n"

# ---------------------------------------------------------------- Lakeflow
lakeflow = ["# Lakeflow evidence: ingestion pipeline `northbeam_ingest`", stamp,
    section("Pipeline updates (event log)", f"""
SELECT timestamp, details:update_progress.state AS state, origin.update_id
FROM event_log('{PIPELINE}') WHERE event_type = 'update_progress' AND details:update_progress.state IN ('COMPLETED','FAILED')
ORDER BY timestamp"""),
    section("Rows written per flow per update", f"""
SELECT timestamp, origin.flow_name, details:flow_progress.metrics.num_output_rows AS output_rows
FROM event_log('{PIPELINE}')
WHERE event_type = 'flow_progress' AND details:flow_progress.status = 'COMPLETED'
  AND details:flow_progress.metrics.num_output_rows IS NOT NULL
ORDER BY timestamp, origin.flow_name"""),
    section("Data quality expectations (passed / failed records)", f"""
SELECT origin.flow_name, e.name AS expectation, e.dataset, sum(e.passed_records) AS passed, sum(e.failed_records) AS failed
FROM event_log('{PIPELINE}'),
     LATERAL explode(from_json(details:flow_progress.data_quality.expectations,
       'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS t(e)
WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL
GROUP BY ALL ORDER BY 1, 2""", "`public_barcode` is a warn-only expectation: failures are the private-label / missing-barcode items that the GenAI tier resolves."),
    section("Silver product master: items per market and first-seen week", f"""
SELECT f.market, f.first_seen_week, count(*) AS items, count(s.gtin13) AS with_public_barcode,
       sum(CASE WHEN s.is_private_label THEN 1 ELSE 0 END) AS private_label
FROM {CS}.silver_item_first_seen f JOIN {CS}.silver_product_item s USING (market, item_id)
GROUP BY ALL ORDER BY 1, 2"""),
]
(OUT / "lakeflow_pipeline.md").write_text("\n".join(lakeflow))

# ---------------------------------------------------------------- Unity Catalog
uc = ["# Unity Catalog evidence: governance, tags, lineage", stamp,
    section("Tables and comments", f"""
SELECT table_name, table_type, comment FROM {CS.split('.')[0]}.information_schema.tables
WHERE table_schema = '{CS.split('.')[1]}' AND table_name NOT LIKE 'work_%' AND table_name NOT LIKE '__materialization%' ORDER BY table_name"""),
    section("Table tags", f"""
SELECT table_name, tag_name, tag_value FROM {CS.split('.')[0]}.information_schema.table_tags
WHERE schema_name = '{CS.split('.')[1]}' ORDER BY table_name, tag_name"""),
    section("Column tags", f"""
SELECT table_name, column_name, tag_name, tag_value FROM {CS.split('.')[0]}.information_schema.column_tags
WHERE schema_name = '{CS.split('.')[1]}' ORDER BY table_name"""),
    section("Row filter and column mask on review_history", f"""
SELECT 'row_filter' AS kind, table_name, filter_name AS function_name, target_columns FROM {CS.split('.')[0]}.information_schema.row_filters WHERE table_schema = '{CS.split('.')[1]}'
UNION ALL
SELECT 'column_mask', table_name, mask_name, column_name FROM {CS.split('.')[0]}.information_schema.column_masks WHERE table_schema = '{CS.split('.')[1]}'"""),
    section("Governance functions", f"""
SELECT routine_name, comment FROM {CS.split('.')[0]}.information_schema.routines
WHERE routine_schema = '{CS.split('.')[1]}' ORDER BY routine_name"""),
    section("Lineage (system.access.table_lineage): how data flows between layers", f"""
SELECT DISTINCT source_table_name, target_table_name, entity_type
FROM system.access.table_lineage
WHERE (target_table_catalog = 'milica_test' AND target_table_schema = 'fe_bar_northbeam')
  AND source_table_name IS NOT NULL AND target_table_name IS NOT NULL
  AND target_table_name NOT LIKE 'work_%' AND event_date >= current_date() - INTERVAL 2 DAYS
ORDER BY target_table_name, source_table_name"""),
]
(OUT / "unity_catalog_governance.md").write_text("\n".join(uc))

# ---------------------------------------------------------------- Gold / business results
gold = ["# Gold results: enriched products and KPIs", stamp,
    section("KPIs from the metric view (as Genie and the app see them)", f"""
SELECT market, MEASURE(products) AS products, MEASURE(automation_rate) AS automation_rate,
       MEASURE(attribute_coverage) AS attribute_coverage, MEASURE(products_needing_review) AS needs_review,
       MEASURE(human_verified_products) AS human_verified, MEASURE(high_protein_share) AS high_protein_share
FROM {CS}.mv_enrichment_kpis GROUP BY market ORDER BY market"""),
    section("Segment mix", f"""
SELECT market, coalesce(segment, 'UNRESOLVED') AS segment, count(*) AS products, round(avg(confidence_score), 1) AS avg_confidence
FROM {CS}.gold_product_enrichment GROUP BY ALL ORDER BY market, products DESC"""),
    section("Sample: auto-enriched products (high confidence)", f"""
SELECT market, item_id, descriptor, descriptor_en, evidence_tier, kcal_per_bar, protein_g_per_bar, segment, claimed_ingredient, confidence_score
FROM {CS}.gold_product_enrichment WHERE NOT needs_review AND NOT human_verified ORDER BY confidence_score DESC, item_id LIMIT 10"""),
    section("Sample: name-matched private label (GenAI tier) with explanation", f"""
SELECT market, item_id, descriptor_en, matched_product_name, protein_g_per_bar, segment, confidence_score, needs_review, explanation
FROM {CS}.gold_product_enrichment WHERE evidence_tier = 'name_match' ORDER BY confidence_score DESC LIMIT 8"""),
    section("Sample: sent to analyst review (lowest confidence)", f"""
SELECT market, item_id, descriptor_en, evidence_tier, confidence_score, confidence_factors, explanation
FROM {CS}.gold_product_enrichment WHERE needs_review AND NOT human_verified ORDER BY confidence_score LIMIT 8"""),
    section("Human-in-the-loop: analyst decisions applied to gold", f"""
SELECT market, item_id, segment, protein_g_per_bar, kcal_per_bar, confidence_score, human_verified, explanation
FROM {CS}.gold_product_enrichment WHERE human_verified"""),
    section("Review history (governed: row filter + masked reviewer)", f"""
SELECT market, item_id, action, field, ai_value, corrected_value, reviewer_email, reviewed_at, applied_at FROM {CS}.review_history ORDER BY reviewed_at"""),
    section("Run metrics per weekly delivery (incremental: only new products are enriched)", f"""
SELECT delivery_week, market, products, barcode_exact, name_match, no_evidence, llm_calls, est_cost_usd, cost_per_1000_usd,
       runtime_s, avg_confidence, review_rate, analyst_hours_saved FROM {CS}.run_metrics ORDER BY created_at"""),
    section("Evaluation results history (MLflow run ids)", f"""
SELECT * FROM {CS}.evaluation_results"""),
]
(OUT / "gold_results.md").write_text("\n".join(gold))
print("wrote lakeflow_pipeline.md, unity_catalog_governance.md, gold_results.md")
