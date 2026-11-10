"""Lakebase evidence: what the app reads/writes, synced-table freshness and point-lookup latency.

Usage: python scripts/collect_lakebase_evidence.py <profile> <instance>
"""
import json, statistics, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

import psycopg

PROFILE, INSTANCE = sys.argv[1], sys.argv[2]
cli = lambda *a: json.loads(subprocess.run(["databricks", *a, "-p", PROFILE, "-o", "json"], capture_output=True, text=True).stdout)
inst = cli("database", "get-database-instance", INSTANCE)
token = cli("database", "generate-database-credential", "--json",
            json.dumps({"instance_names": [INSTANCE], "request_id": "evidence"}))["token"]
user = cli("current-user", "me")["userName"]
synced = cli("database", "get-synced-database-table", "northbeam_lakebase.public.gold_product_enrichment")

conn = psycopg.connect(host=inst["read_write_dns"], dbname="northbeam", user=user, password=token, sslmode="require")
out = [f"# Lakebase evidence: operational serving for the review app",
       f"_Collected {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}._", "",
       f"Instance `{INSTANCE}`: state **{inst['state']}**, capacity {inst['capacity']}, {inst.get('pg_version')}.",
       f"Synced table `northbeam_lakebase.public.gold_product_enrichment` ← `milica_test.fe_bar_northbeam.gold_product_enrichment`: "
       f"**{synced['data_synchronization_status']['detailed_state']}**, scheduling policy {synced['spec']['scheduling_policy']}.", ""]


def table(cur, sql, params=()):
    cur.execute(sql, params)
    cols = [d.name for d in cur.description]
    rows = cur.fetchall()
    return ["```sql", sql.strip(), "```", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + \
           ["| " + " | ".join("" if v is None else str(v).replace("|", "/")[:120] for v in r) + " |" for r in rows] + [""]


with conn.cursor() as cur:
    out += ["## Synced gold table in Postgres (what the app reads)"]
    out += table(cur, """SELECT market, count(*) AS products,
                                count(*) FILTER (WHERE needs_review AND NOT human_verified) AS waiting_for_review,
                                count(*) FILTER (WHERE human_verified) AS human_verified, max(updated_at) AS last_update
                         FROM public.gold_product_enrichment GROUP BY market ORDER BY market""")
    out += ["## Review decisions written by the app (OLTP inserts, applied by the weekly job)"]
    out += table(cur, """SELECT decision_id, market, item_id, action, field, ai_value, corrected_value, reviewer_email, reviewed_at, applied
                         FROM review.review_decisions ORDER BY decision_id""")
    lat = []
    cur.execute("SELECT market, item_id FROM public.gold_product_enrichment ORDER BY random() LIMIT 50")
    keys = cur.fetchall()
    for m, i in keys:
        t = time.perf_counter()
        cur.execute("SELECT * FROM public.gold_product_enrichment WHERE market = %s AND item_id = %s", (m, i))
        cur.fetchall()
        lat.append((time.perf_counter() - t) * 1000)
    out += ["## Point-lookup latency (primary key, 50 random products, from a laptop over the internet)",
            f"median {statistics.median(lat):.1f} ms · p95 {sorted(lat)[int(0.95 * len(lat)) - 1]:.1f} ms · max {max(lat):.1f} ms", ""]
    out += ["## Grants for the app service principal"]
    out += table(cur, """SELECT grantee, table_schema, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
                         FROM information_schema.role_table_grants WHERE grantee NOT IN ('PUBLIC', current_user)
                           AND table_schema IN ('public', 'review') GROUP BY 1, 2, 3 ORDER BY 2, 3""")
Path(__file__).resolve().parents[1].joinpath(".exports/lakebase_serving.md").write_text("\n".join(out))
print("wrote evidence/lakebase_serving.md")
