# evaluate · task run 985268703272921 · SUCCESS

Notebook: `3391c275-f1a4-4459-ba81-527632c3dc61` (language: python)

# 03 · Evaluate against the golden set (MLflow)
The synthetic deliveries were generated from known public products, so every item has a ground truth
(`/Volumes/.../golden/golden_labels.csv`; evaluation only, never read by the pipeline).

What matters for the business:
* **Precision of auto-enriched rows**: products that skip review must be right.
* **Automation rate**: share of products that skip review (analyst time saved).
* **Calibration**: accuracy rises with the confidence score, so the review threshold is meaningful.
* **Cost per 1,000 products** and runtime.


```python
dbutils.widgets.text("catalog", "milica_test")
dbutils.widgets.text("schema", "fe_bar_northbeam")
dbutils.widgets.text("experiment", "/Shared/northbeam_product_enrichment")
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
spark.sql(f"USE {catalog}.{schema}")
```

```python
import mlflow

spark.sql(f"""
  CREATE OR REPLACE TEMP VIEW eval_rows AS
  WITH g AS (SELECT * FROM read_files('/Volumes/{catalog}/{schema}/golden/golden_labels.csv', format => 'csv', header => true))
  SELECT e.*, g.kind, lpad(g.true_code, 13, '0') AS true_gtin13,
         cast(g.true_kcal_per_bar AS DOUBLE) AS true_kcal, cast(g.true_protein_g_per_bar AS DOUBLE) AS true_protein,
         CASE WHEN g.true_code IS NULL THEN e.matched_gtin13 IS NULL
              ELSE e.matched_gtin13 = lpad(g.true_code, 13, '0') END AS correct_match,
         abs(e.protein_g_per_bar - cast(g.true_protein_g_per_bar AS DOUBLE)) <= 1 AS protein_ok
  FROM gold_product_enrichment e JOIN g ON g.market = e.market AND g.item_id = e.item_id
""")

overall = spark.sql("""
  SELECT count(*) AS products,
         avg(CASE WHEN NOT needs_review THEN 1 ELSE 0 END) AS automation_rate,
         avg(CASE WHEN correct_match THEN 1 ELSE 0 END) FILTER (WHERE NOT needs_review AND NOT human_verified) AS auto_precision,
         avg(CASE WHEN protein_ok THEN 1 ELSE 0 END) FILTER (WHERE NOT needs_review AND NOT human_verified AND true_protein IS NOT NULL) AS auto_protein_within_1g,
         avg(CASE WHEN correct_match THEN 1 ELSE 0 END) AS match_accuracy_all,
         avg(abs(kcal_per_bar - true_kcal)) FILTER (WHERE correct_match) AS kcal_mae_when_matched,
         avg(abs(protein_g_per_bar - true_protein)) FILTER (WHERE correct_match) AS protein_mae_when_matched,
         avg(CASE WHEN needs_review THEN 1 ELSE 0 END) FILTER (WHERE NOT correct_match) AS wrong_matches_caught_by_review
  FROM eval_rows
""").toPandas()

by_kind = spark.sql("""
  SELECT kind, count(*) AS products,
         round(avg(CASE WHEN correct_match THEN 1 ELSE 0 END), 3) AS match_accuracy,
         round(avg(CASE WHEN NOT needs_review THEN 1 ELSE 0 END), 3) AS automation_rate,
         round(avg(CASE WHEN correct_match THEN 1 ELSE 0 END) FILTER (WHERE NOT needs_review), 3) AS auto_precision,
         round(avg(confidence_score), 1) AS avg_confidence
  FROM eval_rows GROUP BY kind ORDER BY products DESC
""").toPandas()

calibration = spark.sql("""
  SELECT CASE WHEN confidence_score >= 90 THEN '90-100' WHEN confidence_score >= 70 THEN '70-89'
              WHEN confidence_score >= 50 THEN '50-69' WHEN confidence_score >= 30 THEN '30-49' ELSE '0-29' END AS confidence_bucket,
         count(*) AS products, round(avg(CASE WHEN correct_match THEN 1 ELSE 0 END), 3) AS match_accuracy
  FROM eval_rows GROUP BY 1 ORDER BY 1 DESC
""").toPandas()

runs = spark.sql("""SELECT delivery_week, market, products, cost_per_1000_usd, runtime_s, review_rate, analyst_hours_saved
                    FROM run_metrics ORDER BY created_at""").toPandas()

mlflow.set_experiment(dbutils.widgets.get("experiment"))
with mlflow.start_run(run_name=f"eval_{runs['delivery_week'].max() if len(runs) else 'na'}"):
    mlflow.log_params({"model_resolve": spark.sql("SELECT first(model_resolve) m FROM gold_product_enrichment").first().m,
                       "model_judge": spark.sql("SELECT first(model_judge) m FROM gold_product_enrichment").first().m,
                       "definitions_version": spark.sql("SELECT max(definitions_version) v FROM gold_product_enrichment").first().v})
    mlflow.log_metrics({k: float(v) for k, v in overall.iloc[0].items() if v is not None})
    if len(runs):
        mlflow.log_metrics({"cost_per_1000_usd_avg": float(runs["cost_per_1000_usd"].mean()),
                            "analyst_hours_saved_total": float(runs["analyst_hours_saved"].sum())})
    mlflow.log_table(by_kind, "accuracy_by_kind.json")
    mlflow.log_table(calibration, "calibration.json")
    mlflow.log_table(runs, "run_metrics.json")
    run_id = mlflow.active_run().info.run_id

print("OVERALL"); print(overall.T.to_string(header=False))
print("\nBY PRODUCT KIND"); print(by_kind.to_string(index=False))
print("\nCALIBRATION (accuracy per confidence bucket)"); print(calibration.to_string(index=False))
print("\nRUNS"); print(runs.to_string(index=False))
print(f"\nMLflow run: {run_id}")
spark.createDataFrame(overall.assign(mlflow_run_id=run_id)).write.mode("append").option("mergeSchema", True).saveAsTable("evaluation_results")
dbutils.notebook.exit(overall.to_json(orient="records"))
```
**Output:**
```text
notebook exit value: [{"products":553,"automation_rate":0.6292947559,"auto_precision":1.0,"auto_protein_within_1g":0.9971014493,"match_accuracy_all":0.9294755877,"kcal_mae_when_matched":0.0123752495,"protein_mae_when_matched":0.0001996008,"wrong_matches_caught_by_review":1.0}]
```