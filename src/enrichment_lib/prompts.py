"""Prompts and JSON schemas for the two LLM steps (used with ai_query responseFormat).

Design rule: the LLM never produces nutrition numbers. Numbers come from the
structured public reference. The LLM does what rules cannot: decide *which*
reference product (if any) is the same product as a messy retailer descriptor,
and judge qualitative positioning (diet / fruit_nut / indulgent / wholesome).
"""

import json

RESOLVE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "product_resolution",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "matched_gtin13": {"type": ["string", "null"],
                                   "description": "GTIN of the candidate that is the same product, or null"},
                "identity_match": {"type": "number",
                                   "description": "0-1, how sure the matched candidate is this exact product"},
                "is_snack_bar": {"type": "boolean"},
                "positioning": {"type": "string", "enum": ["diet", "fruit_nut", "indulgent", "wholesome"]},
                "claimed_ingredient": {"type": "string",
                                       "enum": ["OATS", "NUTS", "FRUIT", "WHEAT FLOUR", "RICE", "SEEDS",
                                                "PROTEIN BLEND", "CHOCOLATE", "OTHER"]},
                "explanation": {"type": "string", "description": "English, 1-3 sentences, why this candidate"},
            },
            "required": ["matched_gtin13", "identity_match", "is_snack_bar", "positioning",
                         "claimed_ingredient", "explanation"],
            "additionalProperties": False,
        },
    },
}

JUDGE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "resolution_judge",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "same_product": {"type": "number", "description": "0-1, the match is the same product (brand, flavour, size)"},
                "positioning_ok": {"type": "number", "description": "0-1, positioning is supported by name/ingredients"},
                "rationale": {"type": "string"},
            },
            "required": ["same_product", "positioning_ok", "rationale"],
            "additionalProperties": False,
        },
    },
}


def resolve_prompt(product: dict, candidates: list, definitions: dict) -> str:
    positioning = "\n".join(f"- {k}: {v}" for k, v in definitions["positioning_values"].items())
    cand = "\n".join(
        f"[{i + 1}] gtin13={c['gtin13']} | {c.get('brand') or ''} | {c.get('product_name')} | "
        f"pack {c.get('pack_quantity') or 'n/a'} | ingredients: {(c.get('ingredients_text') or '')[:300]}"
        f" | match_type={c['match_type']}"
        for i, c in enumerate(candidates)) or "NO CANDIDATES"
    return f"""You resolve retailer product records to a public product reference for an FMCG
data agency. The retailer descriptor is abbreviated and may be translated.

RETAILER PRODUCT:
{json.dumps(product, ensure_ascii=False)}

REFERENCE CANDIDATES:
{cand}

TASKS
1. matched_gtin13: the candidate that is the SAME product (same brand, same variant/flavour,
   compatible size). A candidate with match_type=barcode_exact shares the retailer barcode: accept it
   unless brand or product type clearly contradict. For match_type=name_match, only accept if brand
   (or, for private label, product type + flavour + size) is consistent. If unsure, return null.
   Never pick a candidate just because it is the closest one.
2. identity_match: 0-1. Exact barcode and consistent name: 0.95-1. Name match with brand and flavour
   consistent: 0.7-0.9. Plausible but uncertain: below 0.6.
3. is_snack_bar: false if this is not a bar (e.g. biscuits, cakes, cereal, powder).
4. positioning (one of):
{positioning}
5. claimed_ingredient: the hero ingredient the product is positioned on.
6. explanation: 1-3 sentences in English.
"""


def judge_prompt(product: dict, matched: dict, resolution: str) -> str:
    return f"""You audit an automated product match. Be strict.

RETAILER PRODUCT: {json.dumps(product, ensure_ascii=False)}
MATCHED REFERENCE PRODUCT: {json.dumps(matched, ensure_ascii=False) if matched else 'NONE'}
RESOLUTION: {resolution}

same_product: 1 if the matched reference is clearly the same product, 0 if a different product
or sibling flavour/size, 0.5 if it cannot be told. If nothing was matched, return 0.
positioning_ok: is the chosen positioning supported by the product name and ingredients?
"""
