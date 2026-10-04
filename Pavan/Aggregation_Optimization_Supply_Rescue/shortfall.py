"""Shortfall detection and service-level analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass
class ShortfallReport:
    requested_quantity_kg: float
    committed_quantity_kg: float
    available_quantity_kg: float
    shortfall_kg: float
    fill_ratio: float
    critical: bool
    causes: list[str] = field(default_factory=list)
    affected_supply_ids: list[str] = field(default_factory=list)


def detect_shortfall(
    requested_quantity_kg: float,
    supplies: Iterable[Any],
    *,
    committed_quantity_kg: float = 0.0,
    max_acceptable_shortfall_percent: float = 0.0,
) -> ShortfallReport:
    if requested_quantity_kg < 0 or committed_quantity_kg < 0:
        raise ValueError("quantities cannot be negative")
    if not 0 <= max_acceptable_shortfall_percent <= 100:
        raise ValueError("max_acceptable_shortfall_percent must be 0..100")

    available = 0.0
    ids: list[str] = []
    causes: list[str] = []

    for supply in supplies:
        qty = max(0.0, float(getattr(supply, "quantity_kg", 0.0)))
        status = str(getattr(supply, "status", "available") or "").lower()
        if status in {"available", "open", "ready"}:
            available += qty
            sid = str(getattr(supply, "id", "") or "")
            if sid:
                ids.append(sid)
        else:
            causes.append(f"Supply {getattr(supply, 'id', 'unknown')} is not available.")

    committed = min(requested_quantity_kg, committed_quantity_kg)
    serviceable = committed + available
    shortfall = max(0.0, requested_quantity_kg - serviceable)
    fill = min(1.0, serviceable / requested_quantity_kg) if requested_quantity_kg else 1.0
    threshold = requested_quantity_kg * max_acceptable_shortfall_percent / 100.0
    critical = shortfall > threshold + 1e-9

    if available <= 0 and requested_quantity_kg > committed:
        causes.append("No uncommitted available supply remains.")
    elif shortfall > 0:
        causes.append("Available supply is insufficient to satisfy demand.")

    return ShortfallReport(
        requested_quantity_kg=round(requested_quantity_kg, 3),
        committed_quantity_kg=round(committed, 3),
        available_quantity_kg=round(available, 3),
        shortfall_kg=round(shortfall, 3),
        fill_ratio=round(fill, 4),
        critical=critical,
        causes=sorted(set(causes)),
        affected_supply_ids=ids,
    )


def calculate_supply_gap(
    demand_by_crop: Mapping[str, float],
    supply_by_crop: Mapping[str, float],
) -> dict[str, float]:
    """Return positive uncovered demand by crop."""
    crops = set(demand_by_crop) | set(supply_by_crop)
    return {
        crop: round(max(0.0, float(demand_by_crop.get(crop, 0.0)) - float(supply_by_crop.get(crop, 0.0))), 3)
        for crop in sorted(crops)
    }
