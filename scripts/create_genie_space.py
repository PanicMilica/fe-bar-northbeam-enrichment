"""Create (or update) the Northbeam Genie space: natural-language access to the enriched product master.

Usage: python scripts/create_genie_space.py <profile> [space_id]
Prints the space id; put it in databricks.yml (variable genie_space_id) for the app.
"""
import json, subprocess, sys, uuid

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "dev"
SPACE_ID = sys.argv[2] if len(sys.argv) > 2 else None
CAT, SCH = "milica_test", "fe_bar_northbeam"
WAREHOUSE = "148ccb90800933a1"
T = lambda t: f"{CAT}.{SCH}.{t}"
uid = lambda: uuid.uuid4().hex

instructions = f"""- Northbeam Retail Insights harmonises retailer product deliveries for FMCG snack brands. Each row of
  {T('gold_product_enrichment')} is one retailer item (market + item_id) enriched with calories and protein
  per bar, snack-bar segment, hero ingredient and an evidence-based confidence score (0-100).
- Markets: ES (Spain) and US. Delivery weeks look like 2026W40; first_enriched_week is when an item was first enriched.
- Segments: HIGH PROTEIN (>= 15 g protein per bar), ENERGY (5-14 g and > 200 kcal), NOURISH (< 200 kcal),
  DIET, TREAT, NOT A SNACK BAR. NULL segment means no public product could be matched (needs an analyst).
- Status: needs_review = true means an analyst must check it; human_verified = true means an analyst approved
  or corrected it (confidence 100). "Auto-enriched" = not needs_review and not human_verified.
- evidence_tier: barcode_exact (barcode found in the public reference), name_match (matched by name with the
  LLM), none (no evidence).
- For KPIs prefer the metric view {T('mv_enrichment_kpis')} with MEASURE(): products, automation_rate,
  attribute_coverage, products_needing_review, avg_confidence, high_protein_share.
- Cost and runtime per run are in {T('run_metrics')} (est_cost_usd, cost_per_1000_usd, analyst_hours_saved).
- Show percentages with one decimal and round kcal/protein to one decimal. Prefer descriptor_en for product names.
"""

examples = [
    ("What share of products was enriched automatically per market?",
     f"SELECT market, MEASURE(automation_rate) AS automation_rate, MEASURE(products) AS products\n"
     f"FROM {T('mv_enrichment_kpis')} GROUP BY market ORDER BY market"),
    ("Which high-protein bars were added in the latest delivery week?",
     f"SELECT market, item_id, descriptor_en, brand, protein_g_per_bar, kcal_per_bar, confidence_score\n"
     f"FROM {T('gold_product_enrichment')}\n"
     f"WHERE segment = 'HIGH PROTEIN' AND first_enriched_week = (SELECT max(first_enriched_week) FROM {T('gold_product_enrichment')})\n"
     f"ORDER BY protein_g_per_bar DESC"),
    ("How much did enrichment cost per 1,000 products and how many analyst hours did it save?",
     f"SELECT delivery_week, market, products, cost_per_1000_usd, analyst_hours_saved\n"
     f"FROM {T('run_metrics')} ORDER BY delivery_week, market"),
]
questions = [
    "What is the high-protein share of snack bars in Spain vs the US?",
    "How many products are waiting for analyst review, by market?",
    "Which brands have the most protein per bar on average?",
    "How did automation rate change from week to week?",
]

space = {
    "version": 2,
    "config": {"sample_questions": [{"id": uid(), "question": [q]} for q in questions]},
    "data_sources": {"tables": sorted([{"identifier": T(t)} for t in
                                        ["gold_product_enrichment", "mv_enrichment_kpis", "run_metrics", "silver_product_item"]],
                                       key=lambda x: x["identifier"])},
    "instructions": {
        "text_instructions": [{"id": uid(), "content": [l + "\n" for l in instructions.strip().split("\n")]}],
        "example_question_sqls": [{"id": uid(), "question": [q], "sql": [l + "\n" for l in s.split("\n")]}
                                  for q, s in examples],
    },
}
for k in ("text_instructions", "example_question_sqls"):
    space["instructions"][k].sort(key=lambda x: x["id"])
space["config"]["sample_questions"].sort(key=lambda x: x["id"])

body = {"title": "Northbeam · Snack Bar Product Intelligence",
        "description": "Ask about enriched snack-bar products: nutrition, segments, review backlog, automation and cost.",
        "warehouse_id": WAREHOUSE, "serialized_space": json.dumps(space)}
if SPACE_ID:
    cmd = ["databricks", "api", "patch", f"/api/2.0/genie/spaces/{SPACE_ID}", "-p", PROFILE, "--json", json.dumps(body)]
else:
    cmd = ["databricks", "api", "post", "/api/2.0/genie/spaces", "-p", PROFILE, "--json", json.dumps(body)]
out = subprocess.run(cmd, capture_output=True, text=True)
print(out.stdout or out.stderr)
