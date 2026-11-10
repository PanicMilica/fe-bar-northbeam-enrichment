"""App evidence: deployment state + the exact queries the app runs, executed against Lakebase.

Usage: python scripts/collect_app_evidence.py <profile> <app_name> <instance>
"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

PROFILE, APP, INSTANCE = sys.argv[1:4]
cli = lambda *a: json.loads(subprocess.run(["databricks", *a, "-p", PROFILE, "-o", "json"], capture_output=True, text=True).stdout)
app = cli("apps", "get", APP)
logs = subprocess.run(["databricks", "apps", "logs", APP, "-p", PROFILE, "--tail-lines", "200"], capture_output=True, text=True).stdout
inst = cli("database", "get-database-instance", INSTANCE)
token = cli("database", "generate-database-credential", "--json", json.dumps({"instance_names": [INSTANCE], "request_id": "app-ev"}))["token"]
conn = psycopg.connect(host=inst["read_write_dns"], dbname="northbeam", user=cli("current-user", "me")["userName"],
                       password=token, sslmode="require")

QUERIES = {
    "Overview KPIs (tab 1)": """SELECT count(*) AS products,
         count(*) FILTER (WHERE NOT needs_review OR human_verified) AS enriched,
         count(*) FILTER (WHERE needs_review AND NOT human_verified) AS to_review,
         count(*) FILTER (WHERE human_verified) AS verified,
         round(avg(confidence_score)::numeric, 1) AS avg_conf
       FROM public.gold_product_enrichment""",
    "New products per delivery week (tab 1 chart)": """SELECT first_enriched_week AS week, count(*) AS new_products,
         count(*) FILTER (WHERE NOT needs_review) AS auto_enriched
       FROM public.gold_product_enrichment GROUP BY 1 ORDER BY 1""",
    "Review queue, first 8 rows (tab 2)": """SELECT g.market, g.item_id, g.descriptor_en, g.evidence_tier, g.matched_product_name,
         g.protein_g_per_bar, g.segment, g.confidence_score
       FROM public.gold_product_enrichment g
       LEFT JOIN (SELECT DISTINCT market, item_id FROM review.review_decisions) d ON d.market = g.market AND d.item_id = g.item_id
       WHERE g.needs_review AND NOT g.human_verified AND d.item_id IS NULL
       ORDER BY g.confidence_score ASC, g.item_id LIMIT 8""",
    "Recent decisions saved from the app (tab 2)": """SELECT market, item_id, action, field, ai_value, corrected_value, reviewer_email, reviewed_at, applied
       FROM review.review_decisions ORDER BY reviewed_at DESC LIMIT 20""",
}
out = ["# Databricks App evidence: `northbeam-enrichment-console`",
       f"_Collected {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}._", "",
       f"* URL: {app['url']} (workspace SSO; not public)",
       f"* App status: **{app['app_status']['state']}** · compute **{app['compute_status']['state']}** · last deployment **{app['active_deployment']['status']['state']}**",
       f"* Resources bound to the app: " + ", ".join(f"`{r['name']}` ({[k for k in r if k not in ('name', 'description')][0]})" for r in app["resources"]),
       f"* Runs as service principal `{app['service_principal_client_id']}`; Postgres grants: SELECT on the synced gold table, SELECT/INSERT on review decisions",
       "* Analyst identity comes from the `X-Forwarded-Email` header and is stored with each decision.", "",
       "Tabs: **Overview** (KPIs from Lakebase) · **Review queue** (approve / correct / reject → `review.review_decisions`) · **Ask Genie** (Genie Conversation API).",
       "Below, the exact SQL the app runs, executed against the same Lakebase database:", ""]
with conn.cursor() as cur:
    for title, q in QUERIES.items():
        cur.execute(q)
        cols = [d.name for d in cur.description]
        out += [f"## {title}", "```sql", q, "```", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        out += ["| " + " | ".join("" if v is None else str(v)[:90] for v in r) + " |" for r in cur.fetchall()] + [""]
app_lines = [l for l in logs.splitlines() if "[BUILD]" in l and ("Deployment" in l or "Starting app" in l or "scan" in l)][-6:]
out += ["## Deployment log (last lines)", "```text", *app_lines, "```"]
Path(__file__).resolve().parents[1].joinpath("evidence/app.md").write_text("\n".join(out))
print("wrote evidence/app.md")
