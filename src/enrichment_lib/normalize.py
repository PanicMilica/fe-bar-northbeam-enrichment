"""Barcode and pack-size normalisation."""

import re
from typing import Optional

NON_PUBLIC = {"SENSITIVE", "MASKED", "EXCLUSIVE", "", "0", "N/A"}


def gtin_check_digit(digits: str) -> str:
    """GS1 check digit for a GTIN body (any length, rightmost digit weighted 3)."""
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return str((10 - total % 10) % 10)


def to_gtin13(raw: Optional[str], fmt: str) -> Optional[str]:
    """Normalise a delivery barcode to a 13-digit GTIN, or None if not public.

    fmt:
      ean13                  - already a full EAN/UPC with check digit (ES)
      upc11_no_check         - US feed format: the 11 UPC-A body digits, check digit dropped
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw.upper() in NON_PUBLIC or not raw.isdigit():
        return None
    if fmt == "upc11_no_check":
        if len(raw) != 11:
            return None
        body = raw
        return ("0" + body + gtin_check_digit(body)).zfill(13)
    if fmt == "ean13":
        # Prefix 20-29 codes are retailer in-store codes, not public GTINs.
        if len(raw) == 13 and raw.startswith("20"):
            return None
        return raw.zfill(13)
    raise ValueError(f"unknown barcode format {fmt}")


_SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(KG|G|GR|GRS|ML|OZ)\b", re.I)
_COUNT_RE = re.compile(r"(\d+)\s*(?:UN|CT|COUNT|PK|X)\b", re.I)


def parse_grams(text: Optional[str]) -> Optional[float]:
    """'40 G' -> 40.0, '1,2 KG' -> 1200.0, '1.5 OZ' -> 42.5. None if no weight."""
    if not text:
        return None
    m = _SIZE_RE.search(text)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    unit = m.group(2).upper()
    if unit == "KG":
        return value * 1000
    if unit == "OZ":
        return round(value * 28.3495, 1)
    return value


def parse_count(text: Optional[str]) -> Optional[int]:
    """'6 UN' -> 6, '12' -> 12, 'NOT DETERMINED' -> None."""
    if not text:
        return None
    text = text.strip()
    if text.isdigit():
        return int(text) or None
    m = _COUNT_RE.search(text)
    return int(m.group(1)) if m else None


def unit_weight_g(size_text: Optional[str], count_text: Optional[str]) -> Optional[float]:
    """Weight of one bar = total pack weight / units in pack."""
    grams, count = parse_grams(size_text), parse_count(count_text)
    if grams is None:
        return None
    return round(grams / (count or 1), 1)
