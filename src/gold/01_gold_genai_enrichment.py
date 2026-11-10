# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Enrich new products (GenAI)
# MAGIC For every product that is **new** in silver (never enriched, or enriched under an older definitions version):
# MAGIC 1. **Tier 1 – exact barcode** join to the public reference (free, deterministic).
# MAGIC 2. **Tier 2 – semantic name match** for private label / missing barcodes: `ai_translate` the descriptor,
# MAGIC    embed it, retrieve the top-3 reference candidates by cosine similarity.
# MAGIC 3. **Resolve** with `ai_query` (strict JSON): which candidate is the same product, positioning, hero ingredient.
# MAGIC    The LLM never writes numbers; nutrition comes from the reference.
# MAGIC 4. **Judge** with a cheaper model: is the match really the same product?
# MAGIC 5. **Classify** with deterministic rules (`config/attributes.yml`) and **score** confidence from evidence.
# MAGIC 6. MERGE into `gold_product_enrichment` (human-verified rows are never overwritten) and log run metrics.

# COMMAND ----------

dbutils.widgets.text("catalog", "milica_test")
dbutils.widgets.text("schema", "fe_bar_northbeam")
dbutils.widgets.text("model_extract", "databricks-gpt-5-4-mini")
dbutils.widgets.text("model_judge", "databricks-gpt-5-4-nano")
dbutils.widgets.text("embedding_model", "databricks-bge-large-en")
# List prices used for the cost estimate (USD per 1M tokens); check your region's price list.
dbutils.widgets.text("price_resolve_in", "0.40")
dbutils.widgets.text("price_resolve_out", "1.60")
dbutils.widgets.text("price_judge_in", "0.05")
dbutils.widgets.text("price_judge_out", "0.40")
dbutils.widgets.text("price_embed_in", "0.10")
dbutils.widgets.text("price_translate_per_1k_chars", "0.01")
# Business baseline: manual analyst research per product (minutes) - see BUILD.md section 4
dbutils.widgets.text("manual_minutes_per_product", "6")

W = {k: dbutils.widgets.get(k) for k in [
    "catalog", "schema", "model_extract", "model_judge", "embedding_model", "price_resolve_in",
    "price_resolve_out", "price_judge_in", "price_judge_out", "price_embed_in",
    "price_translate_per_1k_chars", "manual_minutes_per_product"]}
spark.sql(f"USE {W['catalog']}.{W['schema']}")

# COMMAND ----------

import json, os, sys, time, uuid
import numpy as np
import pandas as pd
import yaml
from pyspark.sql import functions as F

sys.path.append(os.path.abspath("../"))
from enrichment_lib.classify import classify_snack_bar
from enrichment_lib.confidence import segment_confidence
from enrichment_lib.evidence import from_reference, resolve_nutrition
from enrichment_lib.prompts import JUDGE_SCHEMA, RESOLVE_SCHEMA, judge_prompt, resolve_prompt

DEFS = yaml.safe_load(open("../../config/attributes.yml"))
t0, run_id = time.time(), str(uuid.uuid4())[:8]

# COMMAND ----------

# MAGIC %md ### Worklist: only products not yet enriched under the current definitions

# COMMAND ----------

work = spark.sql(f"""
  SELECT s.market, s.item_id, s.gtin13, s.descriptor, s.source_language, s.brand, s.is_private_label,
         s.manufacturer, s.size_text, s.pack_count_text, s.unit_weight_g, s.delivery_week
  FROM silver_product_item s
  LEFT ANTI JOIN gold_product_enrichment g
    ON g.market = s.market AND g.item_id = s.item_id AND g.definitions_version >= {DEFS['version']}
""")
n_work = work.count()
print(f"worklist: {n_work} new products")
display(work.groupBy("market", "delivery_week").count().orderBy("market"))
if n_work == 0:
    dbutils.notebook.exit(json.dumps({"products": 0}))

# COMMAND ----------

# MAGIC %md ### Tier 1 · exact barcode   ·   Tier 2 · translate + embed + top-3 name candidates

# COMMAND ----------

# Translate local-language descriptors once (Databricks AI function), keep English as is.
work = work.withColumn(
    "descriptor_en",
    F.when(F.col("source_language") != "en", F.expr("ai_translate(descriptor, 'en')")).otherwise(F.col("descriptor")))
work.write.mode("overwrite").option("overwriteSchema", True).saveAsTable("work_items")
work = spark.table("work_items")

exact = spark.sql("""
  SELECT w.market, w.item_id, r.* FROM work_items w JOIN silver_public_reference r ON r.gtin13 = w.gtin13
""").toPandas()
print(f"tier 1 exact barcode matches: {len(exact)}")

# Reference embeddings: computed once per reference product, reused by every later run.
# Products that left the reference (e.g. dropped by a data-quality expectation) are removed.
spark.sql("DELETE FROM ref_embeddings WHERE gtin13 NOT IN (SELECT gtin13 FROM silver_public_reference)")
spark.sql(f"""
  INSERT INTO ref_embeddings
  SELECT r.gtin13, r.search_name, ai_query('{W['embedding_model']}', r.search_name), '{W['embedding_model']}', current_timestamp()
  FROM silver_public_reference r LEFT ANTI JOIN ref_embeddings e ON e.gtin13 = r.gtin13
""")
need_names = spark.sql(f"""
  SELECT w.market, w.item_id, w.descriptor_en,
         ai_query('{W['embedding_model']}', concat_ws(' ', w.brand, w.descriptor_en)) AS embedding
  FROM work_items w LEFT ANTI JOIN silver_public_reference r ON r.gtin13 = w.gtin13
""").toPandas()
ref = spark.table("silver_public_reference").toPandas().set_index("gtin13")
emb = spark.sql("SELECT gtin13, embedding FROM ref_embeddings WHERE gtin13 IN (SELECT gtin13 FROM silver_public_reference)").toPandas()
R = np.vstack(emb["embedding"].map(np.array).values).astype("float32")
R /= np.linalg.norm(R, axis=1, keepdims=True)
print(f"tier 2 name matching for {len(need_names)} products against {len(R)} reference products")

name_candidates = {}
for row in need_names.itertuples():
    q = np.array(row.embedding, dtype="float32")
    q /= np.linalg.norm(q)
    sims = R @ q
    top = np.argsort(-sims)[:3]
    name_candidates[(row.market, row.item_id)] = [(emb["gtin13"].iloc[i], float(sims[i])) for i in top]

# COMMAND ----------

# MAGIC %md ### Resolve (gpt-5.4-mini, strict JSON) and judge (gpt-5.4-nano)

# COMMAND ----------

items = work.toPandas()
exact_by_key = {(r.market, r.item_id): r for r in exact.itertuples()}
REF_COLS = ["brand", "product_name", "pack_quantity", "ingredients_text", "serving_g",
            "kcal_100g", "protein_100g", "kcal_serving", "protein_serving"]


def ref_dict(gtin, match_type, similarity=None):
    r = ref.loc[gtin]
    d = {"gtin13": gtin, "match_type": match_type, "similarity": similarity}
    d.update({c: (None if pd.isna(r[c]) else r[c]) for c in REF_COLS if c in r})
    return d


rows, evidence_rows = [], []
for it in items.itertuples():
    key = (it.market, it.item_id)
    if key in exact_by_key:
        cands = [ref_dict(exact_by_key[key].gtin13, "barcode_exact", 1.0)]
    else:
        cands = [ref_dict(g, "name_match", s) for g, s in name_candidates.get(key, [])]
    product = {"descriptor": it.descriptor, "descriptor_en": it.descriptor_en, "brand": it.brand,
               "private_label": bool(it.is_private_label), "pack": f"{it.size_text} / {it.pack_count_text}",
               "unit_weight_g": it.unit_weight_g}
    rows.append({"market": it.market, "item_id": it.item_id, "product_json": json.dumps(product, ensure_ascii=False),
                 "candidates_json": json.dumps(cands, ensure_ascii=False, default=str),
                 "prompt": resolve_prompt(product, cands, DEFS)})
    for rank, c in enumerate(cands, 1):
        evidence_rows.append({"market": it.market, "item_id": it.item_id, "delivery_week": it.delivery_week,
                              "candidate_rank": rank, "match_type": c["match_type"], "candidate_gtin13": c["gtin13"],
                              "candidate_name": c.get("product_name"), "similarity": c.get("similarity")})

spark.createDataFrame(pd.DataFrame(rows)).createOrReplaceTempView("resolve_input")
fmt = json.dumps(RESOLVE_SCHEMA).replace("'", "\\'")
spark.sql(f"""
  SELECT *, ai_query('{W['model_extract']}', prompt, responseFormat => '{fmt}', failOnError => false) AS res
  FROM resolve_input
""").write.mode("overwrite").option("overwriteSchema", True).saveAsTable("work_resolved")  # materialise once
resolved = spark.table("work_resolved").toPandas()

judge_rows = []
for r in resolved.itertuples():
    res = json.loads(r.res["result"]) if r.res and r.res["result"] else {}
    cands = {c["gtin13"]: c for c in json.loads(r.candidates_json)}
    matched = cands.get(res.get("matched_gtin13"))
    judge_rows.append({"market": r.market, "item_id": r.item_id,
                       "judge_prompt": judge_prompt(json.loads(r.product_json), matched, json.dumps(res))})
spark.createDataFrame(pd.DataFrame(judge_rows)).createOrReplaceTempView("judge_input")
jfmt = json.dumps(JUDGE_SCHEMA).replace("'", "\\'")
spark.sql(f"""
  SELECT *, ai_query('{W['model_judge']}', judge_prompt, responseFormat => '{jfmt}', failOnError => false) AS jdg
  FROM judge_input
""").write.mode("overwrite").option("overwriteSchema", True).saveAsTable("work_judged")
judged = spark.table("work_judged").toPandas().set_index(["market", "item_id"])
errors = int(resolved["res"].map(lambda x: bool(x and x["errorMessage"])).sum())
print(f"resolved {len(resolved)} products, {errors} LLM errors")

# COMMAND ----------

# MAGIC %md ### Classify (rules) and score (evidence-based confidence)

# COMMAND ----------

min_conf = DEFS["review"]["min_confidence"]
out, chosen = [], set()
for r in resolved.itertuples():
    res = json.loads(r.res["result"]) if r.res and r.res["result"] else {}
    jr = judged.loc[(r.market, r.item_id)]
    jdg = json.loads(jr.jdg["result"]) if jr.jdg and jr.jdg["result"] else {}
    product = json.loads(r.product_json)
    cands = {c["gtin13"]: c for c in json.loads(r.candidates_json)}
    m = cands.get(res.get("matched_gtin13"))
    judge = round(0.7 * float(jdg.get("same_product", 0)) + 0.3 * float(jdg.get("positioning_ok", 0)), 2) if jdg else None

    if m:
        chosen.add((r.market, r.item_id, m["gtin13"]))
        tier = m["match_type"]
        identity = 1.0 if tier == "barcode_exact" else float(res.get("identity_match") or 0)
        ev = resolve_nutrition(from_reference(m, tier, identity), product.get("unit_weight_g"))
        kcal, protein = ev.kcal_per_bar, ev.protein_g_per_bar
        if (kcal is not None and not 20 <= kcal <= 700) or (protein is not None and protein > 60):
            kcal, protein = None, None  # implausible per-bar value (bad pack size or source data)
        evidence = [ev]
    else:
        tier, kcal, protein, evidence = "none", None, None, []

    if not res.get("is_snack_bar", True):
        # Out of scope for snack-bar segments; confidence is about the identification only.
        segment, sub_segment = "NOT A SNACK BAR", None
        conf = segment_confidence(evidence, False, False, False, judge) if evidence else {"score": 0, "factors": {"evidence": "none"}}
        reason = "Not a snack bar (e.g. biscuit or cookie): snack-bar segmentation not applicable."
    elif kcal is None and protein is None:
        segment, sub_segment = None, None
        conf = {"score": 0, "factors": {"evidence": "none"}}
        reason = "No public product matched with enough certainty: sent to analyst review."
    else:
        seg = classify_snack_bar(protein, kcal, res.get("positioning"), DEFS)
        conf = segment_confidence(evidence, seg.borderline, seg.missing_inputs, seg.fallback, judge)
        segment, sub_segment, reason = seg.segment, seg.sub_segment, seg.reason

    src = f" Source: {m['product_name']} (GTIN {m['gtin13']}, Open Food Facts, {tier})." if m else ""
    out.append({
        "market": r.market, "item_id": r.item_id, "matched_gtin13": m["gtin13"] if m else None,
        "matched_product_name": m.get("product_name") if m else None,
        "kcal_per_bar": kcal, "protein_g_per_bar": protein, "segment": segment, "sub_segment": sub_segment,
        "claimed_ingredient": res.get("claimed_ingredient"), "positioning": res.get("positioning"),
        "confidence_score": int(conf["score"]), "confidence_factors": json.dumps(conf["factors"]),
        "evidence_tier": tier, "explanation": f"{reason} {res.get('explanation', '')}{src}".strip(),
        "needs_review": int(conf["score"]) < min_conf,
    })

GOLD_SCHEMA = ("market string, item_id string, matched_gtin13 string, matched_product_name string, "
               "kcal_per_bar double, protein_g_per_bar double, segment string, sub_segment string, "
               "claimed_ingredient string, positioning string, confidence_score int, confidence_factors string, "
               "evidence_tier string, explanation string, needs_review boolean, gtin13 string, descriptor string, "
               "descriptor_en string, brand string, is_private_label boolean, delivery_week string")
gold_new = pd.DataFrame(out).merge(
    items[["market", "item_id", "gtin13", "descriptor", "descriptor_en", "brand", "is_private_label", "delivery_week"]],
    on=["market", "item_id"])
gold_new = gold_new[[c.split()[0] for c in GOLD_SCHEMA.split(", ")]]
clean = lambda df: df.astype(object).where(pd.notna(df), None)
sdf = (spark.createDataFrame(clean(gold_new), schema=GOLD_SCHEMA)
       .withColumnRenamed("delivery_week", "first_enriched_week")
       .withColumn("human_verified", F.lit(False)).withColumn("reviewed_by", F.lit(None).cast("string"))
       .withColumn("definitions_version", F.lit(DEFS["version"]))
       .withColumn("model_resolve", F.lit(W["model_extract"])).withColumn("model_judge", F.lit(W["model_judge"]))
       .withColumn("updated_at", F.current_timestamp())
       .select(*spark.table("gold_product_enrichment").columns))
sdf.createOrReplaceTempView("gold_updates")
spark.sql("""
  MERGE INTO gold_product_enrichment t USING gold_updates s
  ON t.market = s.market AND t.item_id = s.item_id
  WHEN MATCHED AND NOT t.human_verified THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *
""")
ev = pd.DataFrame(evidence_rows)
ev["chosen"] = [(a, b, c) in chosen for a, b, c in zip(ev.market, ev.item_id, ev.candidate_gtin13)]
EV_SCHEMA = ("market string, item_id string, delivery_week string, candidate_rank int, match_type string, "
             "candidate_gtin13 string, candidate_name string, similarity double, chosen boolean")
(spark.createDataFrame(clean(ev[[c.split()[0] for c in EV_SCHEMA.split(", ")]]), schema=EV_SCHEMA)
 .withColumn("created_at", F.current_timestamp()).write.mode("append").saveAsTable("evidence"))

# COMMAND ----------

# MAGIC %md ### Run metrics: cost, runtime, review rate, analyst hours saved

# COMMAND ----------

tok = lambda s: len(s or "") / 4.0  # ~4 characters per token (estimate; exact usage in system.serving)
f = lambda k: float(W[k])
cost_resolve = sum(tok(p) * f("price_resolve_in") + 120 * f("price_resolve_out") for p in resolved["prompt"]) / 1e6
cost_judge = sum(tok(p) * f("price_judge_in") + 60 * f("price_judge_out") for p in pd.DataFrame(judge_rows)["judge_prompt"]) / 1e6
cost_embed = sum(tok(t) for t in need_names["descriptor_en"]) * f("price_embed_in") / 1e6
cost_tr = sum(len(d or "") for d, l in zip(items.descriptor, items.source_language) if l != "en") / 1000 * f("price_translate_per_1k_chars")
runtime = round(time.time() - t0, 1)
metrics = []
for market, g in gold_new.groupby("market"):
    share = len(g) / len(gold_new)
    cost = (cost_resolve + cost_judge + cost_embed + cost_tr) * share
    auto = int((~g["needs_review"]).sum())
    metrics.append({
        "run_id": run_id, "delivery_week": max(g["delivery_week"]), "market": market, "products": len(g),
        "barcode_exact": int((g.evidence_tier == "barcode_exact").sum()), "name_match": int((g.evidence_tier == "name_match").sum()),
        "no_evidence": int((g.evidence_tier == "none").sum()), "llm_calls": 2 * len(g),
        "est_cost_usd": round(cost, 4), "cost_per_1000_usd": round(cost / len(g) * 1000, 2),
        "runtime_s": runtime, "avg_confidence": round(float(g.confidence_score.mean()), 1),
        "review_rate": round(float(g.needs_review.mean()), 3),
        "analyst_hours_saved": round(auto * f("manual_minutes_per_product") / 60, 1),
    })
spark.createDataFrame(pd.DataFrame(metrics)).withColumn("created_at", F.current_timestamp()) \
     .write.mode("append").saveAsTable("run_metrics")
display(pd.DataFrame(metrics))
print(json.dumps(metrics, indent=2))

# COMMAND ----------

# MAGIC %md ### Sample of enriched products

# COMMAND ----------

display(spark.sql("""
  SELECT market, item_id, descriptor_en, evidence_tier, kcal_per_bar, protein_g_per_bar, segment, sub_segment,
         claimed_ingredient, confidence_score, needs_review, explanation
  FROM gold_product_enrichment ORDER BY updated_at DESC, confidence_score DESC LIMIT 15
"""))

# COMMAND ----------

dbutils.notebook.exit(json.dumps({"products": int(len(gold_new)), "runtime_s": runtime}))
