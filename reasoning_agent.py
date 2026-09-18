# agents/reasoning_agent.py

"""
Reasoning Agent
---------------
Handles:
1. Missing environmental information
2. Multi-metric environmental reasoning
3. Cross-variable relationships required by the
   Darukaa.Earth AI Biodiversity Intelligence Challenge

Required relationships:
- Soil health ↔ Biodiversity
- Water availability ↔ Species survival
- Land use ↔ Habitat fragmentation
"""

from typing import Dict, List, Any


# ============================================================
# REQUIRED ENVIRONMENTAL FIELDS
# ============================================================

REQUIRED_FIELDS = [
    "soil_ph",
    "soil_organic_carbon",
    "soil_moisture",
    "land_use",
    "biodiversity_indicator",
    "temperature",
    "rainfall",
    "human_impact",
    "crop",
    "region",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean(value: Any) -> str:
    """Convert a value safely to lowercase text."""
    if value is None:
        return ""

    return str(value).strip().lower()


def _has_value(data: Dict[str, Any], field: str) -> bool:
    """Check whether a field contains a meaningful value."""
    value = data.get(field)

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return True


def _number(value: Any):
    """
    Extract a numeric value from strings such as:
    '0.3%', '30', '6.7'.
    """
    if value is None:
        return None

    try:
        text = str(value).replace("%", "").strip()

        # Handle simple numeric values
        return float(text)

    except (ValueError, TypeError):
        return None


# ============================================================
# MISSING FIELD DETECTION
# ============================================================

def missing_fields(data: Dict[str, Any]) -> List[str]:
    """
    Return environmental fields that are not currently available.

    The challenge requires clarification when environmental
    inputs are incomplete.
    """

    data = data or {}

    missing = []

    for field in REQUIRED_FIELDS:
        if not _has_value(data, field):
            missing.append(field)

    return missing


# ============================================================
# ENVIRONMENTAL VARIABLE GROUPS
# ============================================================

def get_variable_groups(data: Dict[str, Any]) -> List[str]:
    """
    Detect broad environmental variable groups.

    Groups:
    - soil
    - land
    - climate
    - biodiversity
    - human_impact
    """

    data = data or {}

    groups = []

    # --------------------------------------------------------
    # Soil health
    # --------------------------------------------------------

    soil_fields = [
        "soil_ph",
        "soil_organic_carbon",
        "soil_moisture",
    ]

    if any(_has_value(data, field) for field in soil_fields):
        groups.append("soil")

    # --------------------------------------------------------
    # Land use / land cover
    # --------------------------------------------------------

    if _has_value(data, "land_use") or _has_value(data, "crop"):
        groups.append("land")

    # --------------------------------------------------------
    # Climate
    # --------------------------------------------------------

    climate_fields = [
        "temperature",
        "rainfall",
    ]

    if any(_has_value(data, field) for field in climate_fields):
        groups.append("climate")

    # --------------------------------------------------------
    # Biodiversity
    # --------------------------------------------------------

    if _has_value(data, "biodiversity_indicator"):
        groups.append("biodiversity")

    # --------------------------------------------------------
    # Human impact
    # --------------------------------------------------------

    if _has_value(data, "human_impact"):
        groups.append("human_impact")

    return groups


# ============================================================
# CROSS-VARIABLE REASONING
# ============================================================

def build_cross_variable_reasoning(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build the three cross-variable relationships explicitly
    required by the Darukaa.Earth challenge.

    The relationships are generated conditionally from the
    environmental context instead of being blindly displayed.
    """

    data = data or {}

    reasoning = []

    soil_carbon = _clean(data.get("soil_organic_carbon"))
    soil_moisture = _clean(data.get("soil_moisture"))
    biodiversity = _clean(data.get("biodiversity_indicator"))

    rainfall = _clean(data.get("rainfall"))
    land_use = _clean(data.get("land_use"))
    crop = _clean(data.get("crop"))

    # ========================================================
    # 1. SOIL HEALTH ↔ BIODIVERSITY
    # ========================================================

    has_soil = (
        bool(soil_carbon)
        or bool(soil_moisture)
        or _has_value(data, "soil_ph")
    )

    has_biodiversity = bool(biodiversity)

    if has_soil and has_biodiversity:

        soil_condition = []

        if soil_carbon:
            soil_condition.append(
                f"soil organic carbon is {soil_carbon}"
            )

        if soil_moisture:
            soil_condition.append(
                f"soil moisture is {soil_moisture}"
            )

        if soil_condition:
            condition_text = " and ".join(soil_condition)

            explanation = (
                f"The environmental profile indicates that "
                f"{condition_text}. These soil-health conditions "
                f"are considered together with the biodiversity "
                f"indicator ({biodiversity})."
            )
        else:
            explanation = (
                "Soil-health information is available and is "
                "being considered together with the biodiversity "
                "indicator."
            )

        reasoning.append({
            "relationship": "Soil health ↔ Biodiversity",
            "explanation": explanation,
            "variables": (
                "soil organic carbon, soil moisture, "
                "soil pH, biodiversity indicator"
            ),
        })

    # ========================================================
    # 2. WATER AVAILABILITY ↔ SPECIES SURVIVAL
    # ========================================================

    has_water_information = (
        bool(rainfall)
        or bool(soil_moisture)
    )

    if has_water_information and has_biodiversity:

        water_conditions = []

        if rainfall:
            water_conditions.append(
                f"rainfall is {rainfall}"
            )

        if soil_moisture:
            water_conditions.append(
                f"soil moisture is {soil_moisture}"
            )

        water_text = " and ".join(water_conditions)

        explanation = (
            f"Water availability is represented by {water_text}. "
            f"This is considered together with the biodiversity "
            f"indicator ({biodiversity}) because water availability "
            f"is a relevant environmental condition for species "
            f"survival."
        )

        reasoning.append({
            "relationship": "Water availability ↔ Species survival",
            "explanation": explanation,
            "variables": (
                "rainfall, soil moisture, "
                "biodiversity indicator"
            ),
        })

    # ========================================================
    # 3. LAND USE ↔ HABITAT FRAGMENTATION
    # ========================================================

    has_land_information = (
        bool(land_use)
        or bool(crop)
    )

    if has_land_information and has_biodiversity:

        land_conditions = []

        if land_use:
            land_conditions.append(
                f"land use is {land_use}"
            )

        if crop:
            land_conditions.append(
                f"crop context is {crop}"
            )

        land_text = " and ".join(land_conditions)

        explanation = (
            f"The land profile indicates that {land_text}. "
            f"This is considered together with the biodiversity "
            f"indicator ({biodiversity}) when assessing habitat "
            f"conditions and potential habitat fragmentation."
        )

        reasoning.append({
            "relationship": "Land use ↔ Habitat fragmentation",
            "explanation": explanation,
            "variables": (
                "land use, crop, biodiversity indicator"
            ),
        })

    return reasoning


# ============================================================
# MAIN REASONING FUNCTION
# ============================================================

def reason(query: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform multi-metric environmental reasoning.

    Returns a structured dictionary so the existing Streamlit
    application can display the analysis.
    """

    data = data or {}
    query = query or ""

    groups = get_variable_groups(data)

    cross_variable_reasoning = build_cross_variable_reasoning(data)

    missing = missing_fields(data)

    # --------------------------------------------------------
    # Determine whether enough variable groups are available
    # for multi-metric reasoning.
    # --------------------------------------------------------

    if len(groups) >= 3:
        reasoning_status = "Ready"
        summary = (
            "Multiple environmental variable groups are "
            "available for cross-variable reasoning."
        )

    else:
        reasoning_status = "Needs more data"
        summary = (
            "Additional environmental variables may be required "
            "for stronger multi-metric reasoning."
        )

    # --------------------------------------------------------
    # Build human-readable reasoning text
    # --------------------------------------------------------

    reasoning_points = []

    for item in cross_variable_reasoning:
        reasoning_points.append(
            f"{item['relationship']}: "
            f"{item['explanation']}"
        )

    if not reasoning_points:
        reasoning_points.append(
            "More environmental variables are required to "
            "establish the required cross-variable relationships."
        )

    # --------------------------------------------------------
    # Return structure
    # --------------------------------------------------------

    return {
        "query": query,
        "variable_groups": groups,
        "variable_group_count": len(groups),
        "reasoning_status": reasoning_status,
        "summary": summary,
        "cross_variable_reasoning": cross_variable_reasoning,
        "reasoning_points": reasoning_points,
        "missing_fields": missing,
        "multi_metric": len(groups) >= 3,
    }