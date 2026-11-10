"""Deterministic segment classification from the attribute definitions.

Numbers decide the numeric rules (protein / kcal thresholds); the LLM only
supplies the qualitative `positioning` (diet / fruit_nut / indulgent /
wholesome). This keeps the classification auditable and cheap, and makes the
definitions editable by the business without touching prompts.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SegmentResult:
    segment: str
    sub_segment: str
    rule_index: int
    borderline: bool          # a numeric value sits close to a threshold
    missing_inputs: bool      # a rule needed a number we do not have
    fallback: bool
    reason: str


def _within(value, lo=None, hi=None):
    if value is None:
        return None
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


def _is_borderline(value, thresholds, margin):
    if value is None:
        return False
    return any(t and abs(value - t) <= abs(t) * margin for t in thresholds)


def classify_snack_bar(protein_g: Optional[float], kcal: Optional[float],
                       positioning: Optional[str], definitions: dict) -> SegmentResult:
    rules = definitions["snack_bar_segments"]
    margin = definitions.get("review", {}).get("borderline_margin", 0.10)
    missing_any = False

    for i, seg in enumerate(rules):
        r = seg["rule"]
        if r.get("fallback"):
            return SegmentResult(seg["segment"], seg["sub_segment"], i, False, missing_any, True,
                                 "No definition matched; fallback segment, needs review.")
        checks = []
        if "protein_g_min" in r or "protein_g_max" in r:
            checks.append(("protein", _within(protein_g, r.get("protein_g_min"), r.get("protein_g_max"))))
        if "calories_kcal_min" in r or "calories_kcal_max" in r:
            checks.append(("kcal", _within(kcal, r.get("calories_kcal_min"), r.get("calories_kcal_max"))))
        if "positioning" in r:
            checks.append(("positioning", positioning in r["positioning"] if positioning else None))

        if any(ok is None for _, ok in checks):
            missing_any = True
            continue
        if all(ok for _, ok in checks):
            thresholds_p = [r.get("protein_g_min"), r.get("protein_g_max")]
            thresholds_k = [r.get("calories_kcal_min"), r.get("calories_kcal_max")]
            borderline = _is_borderline(protein_g, thresholds_p, margin) or _is_borderline(kcal, thresholds_k, margin)
            parts = []
            if protein_g is not None:
                parts.append(f"{protein_g:g} g protein")
            if kcal is not None:
                parts.append(f"{kcal:g} kcal")
            if positioning:
                parts.append(f"positioning '{positioning}'")
            return SegmentResult(seg["segment"], seg["sub_segment"], i, borderline, missing_any, False,
                                 f"Per bar: {', '.join(parts)} -> {seg['definition']}")

    raise ValueError("attribute definitions must end with a fallback rule")
