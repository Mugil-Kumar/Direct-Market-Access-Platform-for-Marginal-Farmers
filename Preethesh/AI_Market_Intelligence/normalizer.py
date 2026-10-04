"""
Data normalization utilities for AGRIWEAVE AI.

The marketplace may receive inconsistent farmer and buyer inputs.
This module converts them into predictable values before they
reach filtering and matching.
"""

from datetime import datetime
from typing import Any, Optional


# Common crop aliases.
CROP_ALIASES = {
    "tomatoes": "tomato",
    "tomato": "tomato",
    "potatoes": "potato",
    "potato": "potato",
    "onions": "onion",
    "onion": "onion",
    "chillies": "chilli",
    "chili": "chilli",
    "chilli": "chilli",
    "brinjals": "brinjal",
    "eggplant": "brinjal",
    "ladies finger": "okra",
    "lady finger": "okra",
    "ladies' finger": "okra",
}


# Common quality aliases.
QUALITY_ALIASES = {
    "a": "grade_a",
    "grade a": "grade_a",
    "grade-a": "grade_a",
    "grade_a": "grade_a",
    "premium": "premium",
    "high": "premium",
    "b": "grade_b",
    "grade b": "grade_b",
    "grade-b": "grade_b",
    "grade_b": "grade_b",
    "standard": "standard",
    "medium": "standard",
    "c": "grade_c",
    "grade c": "grade_c",
    "grade-c": "grade_c",
    "grade_c": "grade_c",
}


def normalize_text(value: Any) -> str:
    """
    Normalize general text.

    Example:
        "  TOMATO  " -> "tomato"
    """
    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def normalize_crop(value: Any) -> str:
    """
    Normalize a crop name and resolve common aliases.
    """
    crop = normalize_text(value)

    if not crop:
        return ""

    return CROP_ALIASES.get(crop, crop)


def normalize_quality(value: Any) -> str:
    """
    Normalize quality labels into a small consistent vocabulary.
    """
    quality = normalize_text(value)

    if not quality:
        return ""

    return QUALITY_ALIASES.get(quality, quality)


def normalize_quantity(value: Any) -> Optional[float]:
    """
    Convert quantity into kilograms.

    Supported examples:
        50
        "50"
        "50 kg"
        "1.5 tonnes"
        "1000 g"

    Invalid values return None.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        quantity = float(value)
        return quantity if quantity >= 0 else None

    text = normalize_text(value)

    if not text:
        return None

    units = {
        "kg": 1.0,
        "kgs": 1.0,
        "kilogram": 1.0,
        "kilograms": 1.0,
        "g": 0.001,
        "gram": 0.001,
        "grams": 0.001,
        "ton": 1000.0,
        "tons": 1000.0,
        "tonne": 1000.0,
        "tonnes": 1000.0,
    }

    parts = text.split()

    try:
        if len(parts) == 1:
            return float(parts[0]) if float(parts[0]) >= 0 else None

        number = float(parts[0])
        unit = parts[1]

        if unit not in units:
            return None

        quantity_kg = number * units[unit]

        return quantity_kg if quantity_kg >= 0 else None

    except (TypeError, ValueError):
        return None


def normalize_price(value: Any) -> Optional[float]:
    """
    Normalize a price value to a non-negative float.

    Examples:
        25       -> 25.0
        "₹25"    -> 25.0
        "25/kg"  -> 25.0
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        price = float(value)
        return price if price >= 0 else None

    text = normalize_text(value)

    if not text:
        return None

    cleaned = (
        text.replace("₹", "")
        .replace("rs.", "")
        .replace("rs", "")
        .replace("/kg", "")
        .replace("per kg", "")
        .replace(",", "")
        .strip()
    )

    try:
        price = float(cleaned)
        return price if price >= 0 else None
    except ValueError:
        return None


def normalize_location(value: Any) -> str:
    """
    Normalize a location string.
    """
    return normalize_text(value)


def normalize_datetime(value: Any) -> Optional[str]:
    """
    Normalize common date/time inputs to ISO-8601 strings.

    Existing ISO timestamps are preserved in normalized form.
    Invalid values return None.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    text = str(value).strip()

    if not text:
        return None

    # Handle common ISO format.
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.isoformat()
    except ValueError:
        pass

    common_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
    ]

    for date_format in common_formats:
        try:
            parsed = datetime.strptime(text, date_format)
            return parsed.isoformat()
        except ValueError:
            continue

    return None


def normalize_reliability(value: Any) -> float:
    """
    Normalize farmer/buyer reliability to the range [0, 1].

    Values such as:
        0.85 -> 0.85
        85   -> 0.85
        120  -> 1.0
    """

    if value is None:
        return 0.0

    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    if score < 0:
        return 0.0

    # Treat percentages as 0-100.
    if score > 1:
        score = score / 100.0

    return min(score, 1.0)


def normalize_supply_data(data: dict) -> dict:
    """
    Normalize raw farmer supply data.

    This function does not silently invent missing information.
    Missing/invalid fields remain empty or None so that the
    candidate-filtering layer can reject incomplete records.
    """

    return {
        **data,
        "crop": normalize_crop(data.get("crop")),
        "quantity_kg": normalize_quantity(data.get("quantity_kg")),
        "location": normalize_location(data.get("location")),
        "available_from": normalize_datetime(
            data.get("available_from")
        ),
        "available_until": normalize_datetime(
            data.get("available_until")
        ),
        "quality": normalize_quality(data.get("quality")),
        "expected_price_per_kg": normalize_price(
            data.get("expected_price_per_kg")
        ),
    }


def normalize_demand_data(data: dict) -> dict:
    """
    Normalize raw buyer demand data.
    """

    return {
        **data,
        "crop": normalize_crop(data.get("crop")),
        "quantity_kg": normalize_quantity(data.get("quantity_kg")),
        "destination": normalize_location(
            data.get("destination")
        ),
        "deadline": normalize_datetime(data.get("deadline")),
        "max_price_per_kg": normalize_price(
            data.get("max_price_per_kg")
        ),
        "quality_required": normalize_quality(
            data.get("quality_required")
        ),
    }