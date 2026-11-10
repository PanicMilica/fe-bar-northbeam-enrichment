"""Download a public snapshot of snack-bar products from Open Food Facts.

Open Food Facts is an open database (ODbL licence, https://world.openfoodfacts.org).
This snapshot is the *public product reference* that the pipeline uses as its
first evidence tier, and the source the synthetic retailer deliveries are built from.

Usage: python scripts/fetch_public_reference.py
Writes data/public_reference/off_snack_bars.jsonl
"""
import json, time, urllib.parse, urllib.request
from pathlib import Path

UA = "fe-bar-northbeam-enrichment/0.1 (synthetic FE Bar demo)"
FIELDS = ",".join(["code", "product_name", "product_name_en", "product_name_es", "brands", "quantity",
                   "serving_quantity", "nutriments", "categories_tags", "ingredients_text_en",
                   "ingredients_text", "countries_tags", "labels_tags"])
QUERIES = [  # (country, category, pages)
    ("Spain", "Cereal bars", 4), ("Spain", "Protein bars", 2), ("Spain", "Nut bars", 1),
    ("United States", "Cereal bars", 4), ("United States", "Protein bars", 4), ("United States", "Nut bars", 1),
]
OUT = Path(__file__).resolve().parents[1] / "data/public_reference/off_snack_bars.jsonl"


def get(country, category, page):
    qs = urllib.parse.urlencode({"categories_tags_en": category, "countries_tags_en": country,
                                 "fields": FIELDS, "page_size": 100, "page": page, "sort_by": "unique_scans_n"})
    req = urllib.request.Request(f"https://world.openfoodfacts.org/api/v2/search?{qs}", headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r).get("products", [])
        except Exception as e:  # 429 / 5xx: back off and retry
            print(f"  retry {attempt + 1} after {e}")
            time.sleep(15 * (attempt + 1))
    return []


def usable(p):
    n = p.get("nutriments") or {}
    return bool(p.get("code") and p.get("product_name") and n.get("proteins_100g") is not None
                and n.get("energy-kcal_100g") is not None and len(p["code"]) in (12, 13))


seen, rows = set(), []
for country, category, pages in QUERIES:
    for page in range(1, pages + 1):
        products = get(country, category, page)
        kept = 0
        for p in products:
            if usable(p) and p["code"] not in seen:
                seen.add(p["code"])
                n = p["nutriments"]
                rows.append({
                    "code": p["code"].zfill(13), "product_name": p.get("product_name"),
                    "product_name_en": p.get("product_name_en"), "brands": p.get("brands"),
                    "quantity": p.get("quantity"), "serving_quantity": p.get("serving_quantity"),
                    "kcal_100g": n.get("energy-kcal_100g"), "protein_100g": n.get("proteins_100g"),
                    "sugars_100g": n.get("sugars_100g"), "fat_100g": n.get("fat_100g"),
                    "kcal_serving": n.get("energy-kcal_serving"), "protein_serving": n.get("proteins_serving"),
                    "categories_tags": p.get("categories_tags"), "labels_tags": p.get("labels_tags"),
                    "ingredients_text": p.get("ingredients_text_en") or p.get("ingredients_text"),
                    "countries_tags": p.get("countries_tags"), "query_country": country, "query_category": category,
                })
                kept += 1
        print(f"{country} / {category} p{page}: {len(products)} returned, {kept} kept")
        time.sleep(7)  # Open Food Facts asks for <= 10 search requests per minute

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{len(rows)} products -> {OUT}")
