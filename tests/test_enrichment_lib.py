"""Unit tests for the Spark-free enrichment logic (run: pytest -q tests)."""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from enrichment_lib.classify import classify_snack_bar
from enrichment_lib.confidence import segment_confidence, AUTO_CAP
from enrichment_lib.evidence import Evidence, from_reference, per_bar, resolve_nutrition
from enrichment_lib.normalize import gtin_check_digit, parse_count, parse_grams, to_gtin13, unit_weight_g

DEFS = yaml.safe_load((Path(__file__).resolve().parents[1] / "config/attributes.yml").read_text())


@pytest.mark.parametrize("raw,fmt,expected", [
    ("4029679669901", "ean13", "4029679669901"),
    ("09661931395", "upc11_no_check", "0096619313952"),   # real public UPC, check digit restored
    ("2000190878651", "ean13", None),                     # retailer in-store code
    ("MASKED", "upc11_no_check", None),
    ("N/A", "ean13", None),
    ("0", "ean13", None),
    ("1234", "upc11_no_check", None),                     # wrong length
])
def test_to_gtin13(raw, fmt, expected):
    assert to_gtin13(raw, fmt) == expected


def test_check_digit():
    assert gtin_check_digit("400638133393") == "1"


def test_pack_parsing():
    assert parse_grams("40 G") == 40.0
    assert parse_grams("1,2 KG") == 1200.0
    assert parse_grams("2.0 OZ") == 56.7
    assert parse_count("6") == 6
    assert parse_count("6 UN") == 6
    assert unit_weight_g("150 G", "6") == 25.0


def test_per_bar_prefers_serving_value():
    assert per_bar(210, 400, 50, 40) == 210
    assert per_bar(None, 400, 50, 40) == 200.0
    assert per_bar(None, 400, None, 40) == 160.0
    assert per_bar(None, None, 50, 40) is None


def test_from_reference_and_resolve():
    ev = from_reference({"gtin13": "1", "kcal_100g": 400, "protein_100g": 30, "serving_g": 50}, "barcode_exact", 1.0)
    ev = resolve_nutrition(ev, unit_weight=40)
    assert ev.kcal_per_bar == 200.0 and ev.protein_g_per_bar == 15.0


@pytest.mark.parametrize("protein,kcal,pos,segment", [
    (20, 210, "indulgent", "HIGH PROTEIN"),
    (8, 230, "wholesome", "ENERGY"),
    (2, 95, "indulgent", "TREAT"),
    (3, 120, "fruit_nut", "NOURISH"),
    (3, 120, "wholesome", "NOURISH"),
    (4, 230, "wholesome", "TREAT"),           # no rule -> fallback
])
def test_classify(protein, kcal, pos, segment):
    assert classify_snack_bar(protein, kcal, pos, DEFS).segment == segment


def test_fallback_and_borderline_flags():
    assert classify_snack_bar(4, 230, "wholesome", DEFS).fallback
    assert classify_snack_bar(15.5, 210, "wholesome", DEFS).borderline


def test_confidence_is_capped_and_ordered():
    strong = [Evidence("barcode_exact", "u", "n", 1.0, kcal_per_bar=200, protein_g_per_bar=20)]
    weak = [Evidence("name_match", "u", "n", 0.6, kcal_per_bar=200, protein_g_per_bar=20)]
    s = segment_confidence(strong, False, False, False, 1.0)["score"]
    w = segment_confidence(weak, False, False, False, 0.7)["score"]
    assert s <= AUTO_CAP and s > w
    assert segment_confidence([], False, False, True, None)["score"] < 30
