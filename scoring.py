"""
Transparent, explainable infrastructure priority scoring module.
Calculates demand intensity, equity weighting, redundancy discounts,
and generates human-readable explanations for policymakers.
"""

from typing import Dict, Any, List


def calculate_district_score(district: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate priority score for a single district based on formula:
      demand = min((complaints / (pop / 50000)) / 8, 1.0)
      equity = 1.15 if pop < 100000 else 1.0
      redundancy = 0.55 if funded else 1.0
      score = round((demand * 0.45 + infra_gap * 0.40) * equity * redundancy * 100, 1)
    """
    pop = int(district.get("pop", 1))
    complaints = int(district.get("complaints", 0))
    infra_gap = float(district.get("infra_gap", 0.0))
    funded = bool(district.get("funded", False))

    # Avoid division by zero
    pop_units = max(pop / 50000.0, 0.001)
    complaints_per_50k = round(complaints / pop_units, 1)

    # Core demand metric capped at 1.0
    demand = min(complaints_per_50k / 8.0, 1.0)

    # Equity multiplier for small/underserved regions
    equity = 1.15 if pop < 100000 else 1.0

    # Redundancy adjustment if capital projects are already committed
    redundancy = 0.55 if funded else 1.0

    # Final composite score
    composite_raw = (demand * 0.45 + infra_gap * 0.40) * equity * redundancy * 100.0
    score = round(composite_raw, 1)

    # Generate transparent why string
    funding_phrase = "an existing funded project is active" if funded else "no funded project covers it"
    equity_phrase = " (includes +15% equity boost for underserved <100k pop)" if equity > 1.0 else ""
    gap_percent = int(round(infra_gap * 100))

    why = (
        f"Complaint volume is {complaints_per_50k}x per 50k population, "
        f"infrastructure deficit is {gap_percent}%, {funding_phrase}{equity_phrase}."
    )

    return {
        "name": district["name"],
        "x": district["x"],
        "y": district["y"],
        "pop": pop,
        "complaints": complaints,
        "infra_gap": infra_gap,
        "funded": funded,
        "category": district["category"],
        "score": score,
        "demand": round(demand, 3),
        "complaints_per_50k": complaints_per_50k,
        "equity": equity,
        "redundancy": redundancy,
        "why": why
    }


def rank_districts(districts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score and rank all districts in descending order of priority score."""
    scored = [calculate_district_score(d) for d in districts]
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored
