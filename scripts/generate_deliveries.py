"""Generate synthetic weekly retailer product deliveries for Northbeam Retail Insights.

Northbeam (fictional) harmonises retailer sell-out data for FMCG snack brands.
Every week each market sends a *product dimension* file. It has the product the
retailer sells, but none of the attributes Northbeam's clients pay for
(calories and protein per bar, segment), so analysts research them by hand.

The deliveries are built from the public Open Food Facts snapshot
(data/public_reference/off_snack_bars.jsonl), with the quirks real feeds have:

* ES: Spanish, upper-case, abbreviated descriptors; real EAN-13 barcodes.
* US: 11-digit item codes without the GTIN check digit; sizes in ounces.
* ~12% private label with a masked barcode and the brand hidden.
* ~8% with a missing or broken barcode but a readable brand and name.
* ~5% synthetic private-label products that do not exist anywhere publicly
  (no evidence can be found; these must end up in human review).

Each market gets three weekly deliveries (W1 → W3). Later weeks add new
products and drop a few, so the incremental design can be tested.

A golden file with the true product and true per-bar nutrition is written to
data/golden/ for evaluation only; the pipeline never reads it.

Usage: python scripts/generate_deliveries.py [--seed 7]
"""
import argparse, csv, html, json, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data/public_reference/off_snack_bars.jsonl"
LANDING = ROOT / "data/landing"
GOLDEN = ROOT / "data/golden/golden_labels.csv"

WEEKS = {"ES": ["2026W40", "2026W41", "2026W42"], "US": ["2026W40", "2026W41", "2026W42"]}
SIZES = {"ES": (230, 18, 24), "US": (230, 20, 22)}  # base items W1, new in W2, new in W3

ES_ABBR = [(r"\bbarritas?\b", "BARR"), (r"\bchocolate\b", "CHOC"), (r"\bcereales?\b", "CER"),
           (r"\bproteínas?\b", "PROT"), (r"\bfrutos secos\b", "F.SECOS"), (r"\bcon\b", "C/"),
           (r"\bleche\b", "LCH"), (r"\bavena\b", "AVENA"), (r"\bsabor\b", "SAB")]
PRIVATE_LABEL_ES = ["BARR CER AVENA C/ CHOC NEGRO", "BARR PROT CACAHUETE 20G PROT", "BARR F.SECOS Y MIEL",
                    "BARR CER ARROZ INFLADO C/ LCH", "BARR DATIL Y ANACARDO"]
PRIVATE_LABEL_US = ["CHEWY GRANOLA BAR CHOC CHIP", "PROTEIN BAR PB CRUNCH 20G", "FRUIT & NUT BAR ALMOND",
                    "CRISPY RICE MARSHMALLOW BAR", "OAT & HONEY GRANOLA BAR"]


def grams(quantity):
    if not quantity:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|oz)\b", quantity.lower())
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return {"kg": v * 1000, "oz": v * 28.3495}.get(m.group(2), v)


def per_bar(p):
    """True per-bar nutrition and pack layout for a reference product.

    The bar weight is the one the delivery states (pack weight / units), using the
    public serving size when it is plausible. Per-bar values = per-100 g x bar weight.
    """
    serving = p.get("serving_quantity")
    try:
        serving = float(serving) if serving not in (None, "") else None
    except ValueError:
        serving = None
    pack_g = grams(p.get("quantity"))
    if not serving or serving <= 5 or serving > 120:
        serving = pack_g if pack_g and pack_g <= 80 else None
    if serving is None:
        return None  # no reliable bar weight: not used for the synthetic deliveries
    count = max(1, round(pack_g / serving)) if pack_g else 1
    if count > 24:
        count = 1
    return {
        "unit_weight_g": round(serving, 1), "pack_count": count,
        "pack_weight_g": round(serving * count, 1),
        "kcal_per_bar": round(p["kcal_100g"] * serving / 100, 1),
        "protein_g_per_bar": round(p["protein_100g"] * serving / 100, 1),
    }


def plausible(p):
    return 50 <= (p.get("kcal_100g") or 0) <= 700 and 0 <= (p.get("protein_100g") or -1) <= 100


def es_descriptor(name, brand, unit_g, count):
    d = html.unescape(name).lower()
    for pat, rep in ES_ABBR:
        d = re.sub(pat, rep.lower(), d)
    d = re.sub(r"[^\w\s/.%]", " ", d).upper()
    return re.sub(r"\s+", " ", f"{d} {brand.upper()} {int(unit_g)}G {count}UN").strip()


def us_descriptor(name, brand, unit_g, count):
    oz = round(unit_g / 28.3495, 2)
    d = re.sub(r"[^\w\s&%]", " ", html.unescape(name)).upper()
    return re.sub(r"\s+", " ", f"{brand.upper()} {d} {oz}OZ {count}CT").strip()


def us_item_code(gtin13):
    """US feed drops the check digit and keeps 11 digits (a common retailer quirk)."""
    return gtin13[-12:-1]


def build_market(market, ref, rng):
    pool = [p for p in ref if (p["query_country"] == "Spain") == (market == "ES") and plausible(p) and per_bar(p)]
    rng.shuffle(pool)
    base, add2, add3 = SIZES[market]
    pool = pool[: base + add2 + add3]
    items = []
    for i, p in enumerate(pool):
        nb = per_bar(p)
        brand = (p.get("brands") or "UNBRANDED").split(",")[0].strip()
        name = p.get("product_name") if market == "ES" else (p.get("product_name_en") or p.get("product_name"))
        roll = rng.random()
        kind = "branded"
        barcode = p["code"] if market == "ES" else us_item_code(p["code"])
        shown_brand = brand
        if roll < 0.12:
            kind, barcode, shown_brand = "private_label_masked", "MASKED", "PRIVATE LABEL"
        elif roll < 0.20:
            kind, barcode = "barcode_missing", rng.choice(["", "0", "N/A"])
        desc_fn = es_descriptor if market == "ES" else us_descriptor
        items.append({
            "item_id": f"{market}-{100000 + i}", "barcode": barcode, "kind": kind,
            "descriptor": desc_fn(name, shown_brand if kind != "private_label_masked" else "", nb["unit_weight_g"], nb["pack_count"]),
            "brand": shown_brand, "manufacturer": "" if kind == "private_label_masked" else brand.upper(),
            "flavour": "", "size": (f"{int(nb['pack_weight_g'])} G" if market == "ES" else f"{round(nb['pack_weight_g'] / 28.3495, 1)} OZ"),
            "pack_count": nb["pack_count"], "true_code": p["code"], **nb,
        })
    # Synthetic private-label products with no public footprint at all.
    names = PRIVATE_LABEL_ES if market == "ES" else PRIVATE_LABEL_US
    for j, n in enumerate(names * 2):
        items.insert(rng.randrange(len(items)), {
            "item_id": f"{market}-{900000 + j}", "barcode": "MASKED", "kind": "private_label_unknown",
            "descriptor": f"{n} {rng.choice([25, 30, 35, 40])}{'G' if market == 'ES' else 'G'} {rng.choice([4, 5, 6])}{'UN' if market == 'ES' else 'CT'}",
            "brand": "PRIVATE LABEL", "manufacturer": "", "flavour": "", "size": "", "pack_count": "",
            "true_code": None, "unit_weight_g": None, "pack_count_true": None, "pack_weight_g": None,
            "kcal_per_bar": None, "protein_g_per_bar": None,
        })
    return items[: base + add2 + add3 + 10], base, add2


def write_deliveries(market, items, base, add2, rng):
    weeks = WEEKS[market]
    w1 = items[:base]
    w2 = [x for x in w1 if rng.random() > 0.03] + items[base: base + add2]
    w3 = [x for x in w2 if rng.random() > 0.03] + items[base + add2:]
    lang_cols = {
        "ES": ["CODIGO_ITEM", "EAN", "DESCRIPCION", "MARCA", "FABRICANTE", "TAMANO", "UNIDADES"],
        "US": ["ITEM_ID", "UPC_11", "DESCRIPTION", "BRAND", "MANUFACTURER", "SIZE", "PACK_COUNT"],
    }[market]
    for week, rows in zip(weeks, (w1, w2, w3)):
        out = LANDING / market / week / f"northbeam_{market.lower()}_products_{week}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(lang_cols + ["DELIVERY_WEEK"])
            for x in rows:
                wr.writerow([x["item_id"], x["barcode"], x["descriptor"], x["brand"], x["manufacturer"],
                             x["size"], x["pack_count"], week])
        print(f"{market} {week}: {len(rows)} products -> {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    rng = random.Random(ap.parse_args().seed)
    ref = [json.loads(l) for l in REF.open()]
    golden = []
    for market in ("ES", "US"):
        items, base, add2 = build_market(market, ref, rng)
        write_deliveries(market, items, base, add2, rng)
        golden += [{"market": market, "item_id": x["item_id"], "kind": x["kind"], "true_code": x["true_code"],
                    "true_kcal_per_bar": x["kcal_per_bar"], "true_protein_g_per_bar": x["protein_g_per_bar"],
                    "true_unit_weight_g": x["unit_weight_g"]} for x in items]
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    with GOLDEN.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(golden[0]))
        wr.writeheader()
        wr.writerows(golden)
    kinds = {}
    for g in golden:
        kinds[g["kind"]] = kinds.get(g["kind"], 0) + 1
    print(f"golden labels: {len(golden)} products {kinds} -> {GOLDEN.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
