"""Evidence model and per-bar nutrition resolution.

Every piece of external information is stored as an Evidence row so the
explanation column can cite exactly where each number came from, and the
confidence score can reason about source quality and agreement.
"""

from dataclasses import dataclass, asdict
from typing import Optional

# How much we trust a source tier before looking at the content.
SOURCE_TIER_WEIGHT = {
    "barcode_exact": 0.90,   # exact GTIN match in the public product reference
    "name_match": 0.75,      # semantic name match in the reference, confirmed by the LLM
    "llm_inference": 0.35,   # no evidence, description only
}


@dataclass
class Evidence:
    source_tier: str
    source_url: Optional[str]
    matched_name: Optional[str]
    identity_match: float              # 0-1: is this evidence about *our* product?
    kcal_per_bar: Optional[float] = None
    protein_g_per_bar: Optional[float] = None
    kcal_per_100g: Optional[float] = None
    protein_g_per_100g: Optional[float] = None
    serving_g: Optional[float] = None
    ingredients_text: Optional[str] = None

    def to_dict(self):
        return asdict(self)


def per_bar(per_bar_value: Optional[float], per_100g_value: Optional[float],
            serving_g: Optional[float], unit_weight: Optional[float]) -> Optional[float]:
    """Prefer an explicit per-serving value; otherwise scale per-100 g by bar weight."""
    if per_bar_value is not None:
        return round(float(per_bar_value), 1)
    weight = serving_g or unit_weight
    if per_100g_value is not None and weight:
        return round(float(per_100g_value) * weight / 100.0, 1)
    return None


def resolve_nutrition(ev: Evidence, unit_weight: Optional[float]) -> Evidence:
    """Fill kcal/protein per bar from per-100 g values where needed."""
    ev.kcal_per_bar = per_bar(ev.kcal_per_bar, ev.kcal_per_100g, ev.serving_g, unit_weight)
    ev.protein_g_per_bar = per_bar(ev.protein_g_per_bar, ev.protein_g_per_100g, ev.serving_g, unit_weight)
    return ev


def from_reference(ref: dict, source_tier: str, identity_match: float) -> Evidence:
    """Map a row of the public product reference (silver_public_reference) to Evidence."""
    def num(k):
        v = ref.get(k)
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None
    return Evidence(
        source_tier=source_tier,
        source_url=f"https://world.openfoodfacts.org/product/{ref.get('gtin13')}",
        matched_name=ref.get("product_name"),
        identity_match=identity_match,
        # Per-serving fields in public data are often inconsistent with per-100 g;
        # per-bar values are derived from per-100 g x bar weight instead.
        kcal_per_bar=None,
        protein_g_per_bar=None,
        kcal_per_100g=num("kcal_100g"),
        protein_g_per_100g=num("protein_100g"),
        serving_g=num("serving_g"),
        ingredients_text=ref.get("ingredients_text"),
    )
