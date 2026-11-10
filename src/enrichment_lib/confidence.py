"""Evidence-based confidence score (0-100).

A common anti-pattern is to run the same prompt several times and use the
agreement rate as "confidence"; that saturates at 100 and says nothing about
the evidence. Here the score is built from independent, explainable factors:

  source     - how trustworthy the best source tier is
  identity   - how sure we are the evidence describes *this* product
  agreement  - do independent sources agree on the numbers?
  margin     - is a numeric value close to a segment threshold?
  judge      - LLM-judge grade (cheap model) of evidence vs. explanation
  completeness - did a rule have to skip because a number was missing?

Factors multiply, so one weak factor pulls the score down, and the score is
capped below 100 unless a human has verified the row. The weights are meant
to be calibrated on the golden set (see notebooks/04_evaluate).
"""

from typing import List, Optional

from .evidence import Evidence, SOURCE_TIER_WEIGHT

AUTO_CAP = 95  # only human-verified rows reach 100


def agreement_factor(values: List[float], tolerance: float = 0.15) -> float:
    """1.05 bonus if >=2 sources agree within tolerance, 0.75 if they conflict."""
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return 1.0
    lo, hi = min(values), max(values)
    if hi == 0:
        return 1.05
    spread = (hi - lo) / hi
    return 1.05 if spread <= tolerance else 0.75


# How much the LLM judge can pull the score down, per evidence tier. An exact
# barcode match is already strong evidence (100% correct on the golden set), so
# the judge only nudges it; for a name match the judge is the main safeguard.
JUDGE_WEIGHT = {"barcode_exact": 0.3, "name_match": 1.0, "llm_inference": 1.0}


def segment_confidence(evidence: List[Evidence], borderline: bool, missing_inputs: bool,
                       fallback: bool, judge_score: Optional[float]) -> dict:
    if evidence:
        best = max(evidence, key=lambda e: SOURCE_TIER_WEIGHT[e.source_tier] * e.identity_match)
        source = SOURCE_TIER_WEIGHT[best.source_tier]
        identity = best.identity_match
    else:
        source, identity = SOURCE_TIER_WEIGHT["llm_inference"], 0.5

    agree = min(agreement_factor([e.protein_g_per_bar for e in evidence]),
                agreement_factor([e.kcal_per_bar for e in evidence]))
    margin = 0.75 if borderline else 1.0
    completeness = 0.8 if missing_inputs else 1.0
    tier = max(evidence, key=lambda e: SOURCE_TIER_WEIGHT[e.source_tier]).source_tier if evidence else "llm_inference"
    raw_judge = judge_score if judge_score is not None else 0.85
    judge = 1 - JUDGE_WEIGHT[tier] * (1 - raw_judge)
    fb = 0.5 if fallback else 1.0

    raw = 100 * source * identity * agree * margin * completeness * judge * fb
    score = int(round(min(raw, AUTO_CAP)))
    return {
        "score": score,
        "factors": {
            "source": source, "identity": round(identity, 2), "agreement": agree,
            "margin": margin, "completeness": completeness, "judge": round(judge, 2),
            "fallback": fb,
        },
    }
