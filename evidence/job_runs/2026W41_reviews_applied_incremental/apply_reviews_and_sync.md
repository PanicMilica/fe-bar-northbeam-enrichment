# apply_reviews_and_sync · task run 499588118864819 · SUCCESS

Notebook: `928360b1-1309-4ddb-b1e3-19f0c739926c` (language: python)

# 02 · Close the loop: analyst decisions (Lakebase) → gold (Unity Catalog) → Lakebase
1. Read pending decisions that analysts saved in the review app (`review.review_decisions` in Lakebase).
2. Append them to the governed `review_history` table (row filter by market, reviewer e-mail masked).
3. Apply them to `gold_product_enrichment`: corrected values, `human_verified = true`, confidence 100.
   Human-verified rows are never overwritten by later enrichment runs.
4. Mark the decisions as applied, then refresh the Lakebase synced table so the app shows the new state.


```python
dbutils.widgets.text("catalog", "milica_test")
dbutils.widgets.text("schema", "fe_bar_northbeam")
dbutils.widgets.text("lakebase_instance", "northbeam-enrichment")
dbutils.widgets.text("lakebase_database", "northbeam")
dbutils.widgets.text("synced_table", "northbeam_lakebase.public.gold_product_enrichment")
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
spark.sql(f"USE {catalog}.{schema}")
```

```python
import time, uuid
import pandas as pd
import psycopg
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
inst = w.database.get_database_instance(dbutils.widgets.get("lakebase_instance"))
cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[inst.name])
conn = psycopg.connect(host=inst.read_write_dns, dbname=dbutils.widgets.get("lakebase_database"),
                       user=w.current_user.me().user_name, password=cred.token, sslmode="require")
with conn.cursor() as cur:
    cur.execute("""SELECT decision_id, market, item_id, action, field, ai_value, corrected_value, comment,
                          reviewer_email, reviewed_at FROM review.review_decisions WHERE NOT applied ORDER BY reviewed_at""")
    pending = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
print(f"{len(pending)} pending analyst decisions")
print(pending.to_string(index=False) if len(pending) else "(none)")
```
**Output:**
```text
5 pending analyst decisions
 decision_id market   item_id  action             field ai_value corrected_value comment              reviewer_email                      reviewed_at
           1     ES ES-100000 approve           segment   ENERGY          ENERGY    None analyst@northbeam.example 2026-11-10 17:14:28.907705+00:00
           2     ES ES-100015 correct           segment     None    HIGH PROTEIN    None analyst@northbeam.example 2026-11-10 17:15:15.246487+00:00
           3     ES ES-100015 correct protein_g_per_bar      nan            16.0    None analyst@northbeam.example 2026-11-10 17:15:15.304630+00:00
           4     ES ES-100015 correct      kcal_per_bar      nan           150.0    None analyst@northbeam.example 2026-11-10 17:15:15.352134+00:00
           5     ES ES-100019  reject           segment     None            None    None analyst@northbeam.example 2026-11-10 17:15:27.811693+00:00
```

```python
if len(pending):
    sdf = spark.createDataFrame(pending.astype(object).where(pd.notna(pending), None),
                                "decision_id long, market string, item_id string, action string, field string, ai_value string, "
                                "corrected_value string, comment string, reviewer_email string, reviewed_at timestamp")
    sdf.createOrReplaceTempView("pending_decisions")
    spark.sql("""
      INSERT INTO review_history
      SELECT market, item_id, action, field, ai_value, corrected_value, comment, reviewer_email, reviewed_at, current_timestamp()
      FROM pending_decisions
    """)
    # One row per product: the latest decision wins; corrections are pivoted per field.
    spark.sql("""
      CREATE OR REPLACE TEMP VIEW decision_per_item AS
      SELECT market, item_id,
             max_by(action, reviewed_at) AS action,
             max_by(reviewer_email, reviewed_at) AS reviewer,
             max_by(comment, reviewed_at) AS comment,
             max_by(corrected_value, reviewed_at) FILTER (WHERE field = 'segment') AS segment,
             max_by(corrected_value, reviewed_at) FILTER (WHERE field = 'protein_g_per_bar') AS protein,
             max_by(corrected_value, reviewed_at) FILTER (WHERE field = 'kcal_per_bar') AS kcal
      FROM pending_decisions GROUP BY market, item_id
    """)
    spark.sql("""
      MERGE INTO gold_product_enrichment t USING decision_per_item d
      ON t.market = d.market AND t.item_id = d.item_id
      WHEN MATCHED AND d.action IN ('approve', 'correct') THEN UPDATE SET
        t.segment = coalesce(d.segment, t.segment),
        t.protein_g_per_bar = coalesce(cast(d.protein AS DOUBLE), t.protein_g_per_bar),
        t.kcal_per_bar = coalesce(cast(d.kcal AS DOUBLE), t.kcal_per_bar),
        t.human_verified = true, t.needs_review = false, t.confidence_score = 100,
        t.reviewed_by = d.reviewer,
        t.explanation = concat('HUMAN VERIFIED (', d.action, ')', coalesce(concat(': ', d.comment), ''), '. Previous: ', t.explanation),
        t.updated_at = current_timestamp()
      WHEN MATCHED AND d.action = 'reject' THEN UPDATE SET
        t.segment = NULL, t.sub_segment = NULL, t.kcal_per_bar = NULL, t.protein_g_per_bar = NULL,
        t.matched_gtin13 = NULL, t.matched_product_name = NULL,
        t.human_verified = true, t.needs_review = false, t.confidence_score = 100, t.reviewed_by = d.reviewer,
        t.explanation = concat('HUMAN REJECTED the AI match', coalesce(concat(': ', d.comment), ''), '.'),
        t.updated_at = current_timestamp()
    """)
    with conn.cursor() as cur:
        cur.execute("UPDATE review.review_decisions SET applied = true WHERE decision_id = ANY(%s)",
                    (list(map(int, pending.decision_id)),))
    conn.commit()
    display(spark.sql("SELECT market, item_id, segment, protein_g_per_bar, kcal_per_bar, confidence_score, reviewed_by "
                      "FROM gold_product_enrichment WHERE human_verified ORDER BY updated_at DESC LIMIT 20"))
conn.close()
```
**Output:**
| market | item_id | segment | protein_g_per_bar | kcal_per_bar | confidence_score | reviewed_by |
|---|---|---|---|---|---|---|
| ES | ES-100019 |  |  |  | 100 | analyst@northbeam.example |
| ES | ES-100015 | HIGH PROTEIN | 16.0 | 150.0 | 100 | analyst@northbeam.example |
| ES | ES-100000 | ENERGY | 5.5 | 369.0 | 100 | analyst@northbeam.example |

### Refresh the Lakebase synced table (gold → Postgres) so the app shows this run's results


```python
st = w.database.get_synced_database_table(dbutils.widgets.get("synced_table"))
pipeline_id = st.data_synchronization_status.pipeline_id
update = w.pipelines.start_update(pipeline_id)
for _ in range(90):
    state = w.pipelines.get_update(pipeline_id, update.update_id).update.state.value
    if state in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(10)
print(f"synced table refresh: {state}")
assert state == "COMPLETED", f"Lakebase sync ended in {state}"
print(w.database.get_synced_database_table(dbutils.widgets.get("synced_table")).data_synchronization_status.detailed_state)
```
**Output:**
```text
synced table refresh: COMPLETED
SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
```