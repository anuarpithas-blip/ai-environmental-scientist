import json
import re

import streamlit as st

from rag.knowledge_base import KnowledgeBase
from agents.reasoning_agent import missing_fields, reason
from agents.recommendation_agent import build_recommendations


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Environmental Scientist",
    page_icon="🌱",
    layout="wide"
)


# ============================================================
# BASIC STYLING
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 17px;
        opacity: 0.75;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 26px;
        font-weight: 650;
        margin-top: 25px;
    }

    .pipeline-box {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(120,120,120,0.25);
        text-align: center;
        margin-bottom: 10px;
    }

    .memory-box {
        padding: 14px;
        border-radius: 10px;
        border: 1px solid rgba(120,120,120,0.25);
        margin-bottom: 8px;
    }

    .reasoning-box {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(120,120,120,0.25);
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION MEMORY
# ============================================================

if "environmental_memory" not in st.session_state:
    st.session_state.environmental_memory = {}

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ============================================================
# HELPER: CLEAN VALUES
# ============================================================

def clean_value(value):
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    return value


# ============================================================
# HELPER: EXTRACT ENVIRONMENTAL VALUES FROM TEXT
# ============================================================

def extract_environmental_values(text):

    extracted = {}

    if not text:
        return extracted

    text_lower = text.lower()

    # --------------------------------------------------------
    # Soil organic carbon
    # --------------------------------------------------------

    soc_patterns = [
        r"soil\s+organic\s+carbon\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"soc\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*%"
    ]

    for pattern in soc_patterns:

        match = re.search(pattern, text_lower)

        if match:
            extracted["soil_organic_carbon"] = (
                match.group(1) + "%"
            )
            break

    # --------------------------------------------------------
    # Rainfall
    # --------------------------------------------------------

    if (
        "rainfall is low" in text_lower
        or "low rainfall" in text_lower
    ):
        extracted["rainfall"] = "low"

    elif (
        "rainfall is high" in text_lower
        or "high rainfall" in text_lower
    ):
        extracted["rainfall"] = "high"

    elif (
        "rainfall is moderate" in text_lower
        or "moderate rainfall" in text_lower
    ):
        extracted["rainfall"] = "moderate"

    # --------------------------------------------------------
    # Soil pH
    # --------------------------------------------------------

    ph_patterns = [
        r"soil\s+ph\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)",
        r"ph\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)"
    ]

    for pattern in ph_patterns:

        match = re.search(pattern, text_lower)

        if match:
            extracted["soil_ph"] = match.group(1)
            break

    # --------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------

    moisture_patterns = [
        r"soil\s+moisture\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*%?"
    ]

    for pattern in moisture_patterns:

        match = re.search(pattern, text_lower)

        if match:
            extracted["soil_moisture"] = match.group(1)
            break

    if (
        "soil moisture is low" in text_lower
        or "low soil moisture" in text_lower
    ):
        extracted["soil_moisture"] = "low"

    elif (
        "soil moisture is high" in text_lower
        or "high soil moisture" in text_lower
    ):
        extracted["soil_moisture"] = "high"

    # --------------------------------------------------------
    # Land use
    # --------------------------------------------------------

    if "monoculture" in text_lower:
        extracted["land_use"] = "monoculture"

    elif "agroforestry" in text_lower:
        extracted["land_use"] = "agroforestry"

    elif "forest" in text_lower:
        extracted["land_use"] = "forest"

    elif "cropland" in text_lower:
        extracted["land_use"] = "cropland"

    # --------------------------------------------------------
    # Crop
    # --------------------------------------------------------

    crop_names = [
        "wheat",
        "rice",
        "maize",
        "cotton",
        "sugarcane",
        "millet",
        "groundnut"
    ]

    for crop_name in crop_names:

        if crop_name in text_lower:
            extracted["crop"] = crop_name
            break

    if "monoculture wheat" in text_lower:

        extracted["crop"] = "monoculture wheat"
        extracted["land_use"] = "monoculture"

    # --------------------------------------------------------
    # Region
    # --------------------------------------------------------

    if "semi-arid" in text_lower:
        extracted["region"] = "semi-arid"

    elif "arid" in text_lower:
        extracted["region"] = "arid"

    elif "tropical" in text_lower:
        extracted["region"] = "tropical"

    elif "temperate" in text_lower:
        extracted["region"] = "temperate"

    # --------------------------------------------------------
    # Biodiversity indicator
    # --------------------------------------------------------

    if "species richness" in text_lower:
        extracted["biodiversity_indicator"] = "species richness"

    elif "habitat diversity" in text_lower:
        extracted["biodiversity_indicator"] = "habitat diversity"

    # --------------------------------------------------------
    # Human impact
    # --------------------------------------------------------

    if "pollution" in text_lower:
        extracted["human_impact"] = "pollution"

    elif "deforestation" in text_lower:
        extracted["human_impact"] = "deforestation"

    return extracted


# ============================================================
# HELPER: MERGE MEMORY + CURRENT INPUT
# ============================================================

def merge_environmental_context(previous_memory, current_data):

    merged = {}

    if previous_memory:
        merged.update(previous_memory)

    if current_data:

        for key, value in current_data.items():

            value = clean_value(value)

            if value:
                merged[key] = value

    return merged


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🌱 AI Environmental Scientist</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    "Darukaa.Earth — Biodiversity Intelligence Challenge"
    "<br>"
    "Knowledge-grounded environmental analysis • "
    "Multi-metric reasoning • Evidence-backed recommendations"
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# ANALYSIS PIPELINE
# ============================================================

st.markdown("## 🔬 Analysis Pipeline")

pipeline_cols = st.columns(5)

pipeline_items = [
    ("📝", "Environmental Input"),
    ("🔎", "Knowledge Retrieval"),
    ("🧠", "Multi-Metric Reasoning"),
    ("🌱", "Recommendation"),
    ("📚", "Evidence")
]

for col, (icon, label) in zip(
    pipeline_cols,
    pipeline_items
):

    with col:

        st.markdown(
            f"""
            <div class="pipeline-box">
                <div style="font-size:26px;">{icon}</div>
                <div>{label}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# SIDEBAR — ENVIRONMENTAL PROFILE
# ============================================================

st.sidebar.title("🌍 Environmental Profile")

soil_ph = st.sidebar.text_input(
    "Soil pH",
    value=""
)

soil_organic_carbon = st.sidebar.text_input(
    "Soil Organic Carbon (%)",
    value=""
)

soil_moisture = st.sidebar.text_input(
    "Soil Moisture",
    value=""
)

land_use = st.sidebar.text_input(
    "Land Use",
    value=""
)

biodiversity_indicator = st.sidebar.text_input(
    "Biodiversity Indicator",
    value=""
)

temperature = st.sidebar.text_input(
    "Temperature",
    value=""
)

rainfall = st.sidebar.text_input(
    "Rainfall",
    value=""
)

human_impact = st.sidebar.text_input(
    "Human Impact",
    value=""
)

crop = st.sidebar.text_input(
    "Crop",
    value=""
)

region = st.sidebar.text_input(
    "Region",
    value=""
)


# ============================================================
# SIDEBAR MEMORY STATUS
# ============================================================

st.sidebar.markdown("---")

st.sidebar.markdown("### 🧠 Scientist Memory")

memory_count = len(
    st.session_state.environmental_memory
)

if memory_count:

    st.sidebar.success(
        f"{memory_count} environmental variables remembered"
    )

else:

    st.sidebar.info(
        "No environmental context remembered yet."
    )


if st.sidebar.button("Clear Analysis"):

    st.session_state.environmental_memory = {}
    st.session_state.analysis_history = []
    st.session_state.last_result = None

    st.rerun()


# ============================================================
# MAIN INPUT
# ============================================================

st.markdown(
    "## Describe the environmental situation"
)

st.caption(
    "Describe the problem in natural language or provide structured JSON."
)

query = st.text_area(
    "Text input",
    height=120,
    placeholder=(
        "Example: My soil organic carbon is 0.3% "
        "and rainfall is low."
    )
)


# ============================================================
# STRUCTURED INPUT
# ============================================================

structured_input = st.text_area(
    "Structured input (JSON, optional)",
    value="",
    height=100,
    placeholder=(
        '{"soil_organic_carbon":"0.3%",'
        '"rainfall":"low",'
        '"crop":"monoculture wheat",'
        '"region":"semi-arid"}'
    )
)


# ============================================================
# ANALYSIS BUTTON
# ============================================================

analyze = st.button(
    "🔬 Analyze as AI Environmental Scientist",
    type="primary",
    use_container_width=True
)


# ============================================================
# ANALYSIS
# ============================================================

if analyze:

    if not query.strip() and not structured_input.strip():

        st.warning(
            "Please provide an environmental situation "
            "or structured input."
        )

        st.stop()

    # --------------------------------------------------------
    # 1. Current sidebar data
    # --------------------------------------------------------

    sidebar_data = {
        "soil_ph": soil_ph,
        "soil_organic_carbon": soil_organic_carbon,
        "soil_moisture": soil_moisture,
        "land_use": land_use,
        "biodiversity_indicator": biodiversity_indicator,
        "temperature": temperature,
        "rainfall": rainfall,
        "human_impact": human_impact,
        "crop": crop,
        "region": region
    }

    sidebar_data = {
        key: value
        for key, value in sidebar_data.items()
        if clean_value(value)
    }

    # --------------------------------------------------------
    # 2. Parse structured JSON
    # --------------------------------------------------------

    structured_data = {}

    if structured_input.strip():

        try:

            parsed = json.loads(
                structured_input
            )

            if not isinstance(parsed, dict):

                st.error(
                    "Structured input must be a JSON object."
                )

                st.stop()

            structured_data = {
                key: value
                for key, value in parsed.items()
                if clean_value(value)
            }

        except json.JSONDecodeError:

            st.error(
                "Invalid JSON. Please check the structured input."
            )

            st.stop()

    # --------------------------------------------------------
    # 3. Extract values from natural language
    # --------------------------------------------------------

    text_extracted_data = (
        extract_environmental_values(query)
    )

    # --------------------------------------------------------
    # 4. Combine current information
    # --------------------------------------------------------

    current_data = {}

    current_data.update(
        sidebar_data
    )

    current_data.update(
        structured_data
    )

    current_data.update(
        text_extracted_data
    )

    # --------------------------------------------------------
    # 5. Merge with Scientist Memory
    # --------------------------------------------------------

    previous_memory = dict(
        st.session_state.environmental_memory
    )

    data = merge_environmental_context(
        previous_memory,
        current_data
    )

    # --------------------------------------------------------
    # 6. Update memory
    # --------------------------------------------------------

    st.session_state.environmental_memory = dict(
        data
    )

    # --------------------------------------------------------
    # 7. Retrieval query
    # --------------------------------------------------------

    context_parts = []

    if query.strip():
        context_parts.append(
            query.strip()
        )

    for key, value in data.items():

        context_parts.append(
            f"{key}: {value}"
        )

    retrieval_query = " | ".join(
        context_parts
    )

    # --------------------------------------------------------
    # 8. Knowledge retrieval
    # --------------------------------------------------------

    kb = KnowledgeBase("data")

    # ========================================================
    # TEMPORARY RAG DEBUG
    # ========================================================

    st.write(
        "DEBUG: Knowledge documents loaded:",
        len(kb.documents)
    )

    st.write(
        "DEBUG: Knowledge sources:",
        kb.sources
    )

    try:

        retrieved = kb.search(
            retrieval_query,
            k=4
        )

    except Exception as exc:

        retrieved = []

        st.warning(
            f"Knowledge retrieval encountered an issue: {exc}"
        )

    # --------------------------------------------------------
    # 9. Multi-metric reasoning
    # --------------------------------------------------------

    try:

        analysis = reason(
            query.strip(),
            data
        )

    except Exception as exc:

        analysis = {
            "error": str(exc),
            "cross_variable_reasoning": []
        }

    # --------------------------------------------------------
    # 10. Missing information
    # --------------------------------------------------------

    try:

        missing = missing_fields(
            data
        )

    except Exception:

        missing = []

    # --------------------------------------------------------
    # 11. Recommendations
    # --------------------------------------------------------

    try:

        recommendations = build_recommendations(
            data,
            analysis,
            retrieved
        )

    except Exception as exc:

        recommendations = []

        st.error(
            f"Recommendation generation failed: {exc}"
        )

    # --------------------------------------------------------
    # 12. Save analysis history
    # --------------------------------------------------------

    history_item = {
        "query": query.strip(),
        "context": dict(data),
        "recommendations": recommendations
    }

    st.session_state.analysis_history.append(
        history_item
    )

    st.session_state.last_result = {
        "data": data,
        "retrieved": retrieved,
        "analysis": analysis,
        "missing": missing,
        "recommendations": recommendations
    }


# ============================================================
# DISPLAY LAST RESULT
# ============================================================

result = st.session_state.last_result

if result:

    data = result["data"]
    retrieved = result["retrieved"]
    analysis = result["analysis"]
    missing = result["missing"]
    recommendations = result["recommendations"]

    # ========================================================
    # 1. ENVIRONMENTAL ASSESSMENT
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        "1. Environmental Assessment"
        "</div>",
        unsafe_allow_html=True
    )

    groups = []

    soil_keys = [
        "soil_ph",
        "soil_organic_carbon",
        "soil_moisture"
    ]

    land_keys = [
        "land_use",
        "crop"
    ]

    climate_keys = [
        "temperature",
        "rainfall",
        "region"
    ]

    biodiversity_keys = [
        "biodiversity_indicator"
    ]

    human_keys = [
        "human_impact"
    ]

    if any(
        key in data
        for key in soil_keys
    ):
        groups.append("soil")

    if any(
        key in data
        for key in land_keys
    ):
        groups.append("land")

    if any(
        key in data
        for key in climate_keys
    ):
        groups.append("climate")

    if any(
        key in data
        for key in biodiversity_keys
    ):
        groups.append("biodiversity")

    if any(
        key in data
        for key in human_keys
    ):
        groups.append("human_impact")

    assessment_cols = st.columns(3)

    with assessment_cols[0]:

        st.metric(
            "Variable groups detected",
            len(groups)
        )

    with assessment_cols[1]:

        if len(groups) >= 3:

            st.metric(
                "Multi-metric reasoning",
                "Ready"
            )

        else:

            st.metric(
                "Multi-metric reasoning",
                "Needs more data"
            )

    with assessment_cols[2]:

        try:
            evidence_count = len(
                retrieved
            )

        except Exception:
            evidence_count = 0

        st.metric(
            "Retrieved evidence",
            evidence_count
        )

    st.markdown(
        "### 🔬 Variables considered"
    )

    if groups:

        st.write(
            " • ".join(groups)
        )

    else:

        st.write(
            "No environmental variables detected."
        )

    # ========================================================
    # CROSS-VARIABLE REASONING
    # ========================================================

    st.markdown(
        "### 🧠 Cross-variable reasoning"
    )

    cross_reasoning = []

    if isinstance(
        analysis,
        dict
    ):

        cross_reasoning = analysis.get(
            "cross_variable_reasoning",
            []
        )

    if cross_reasoning:

        for item in cross_reasoning:

            relationship = item.get(
                "relationship",
                "Environmental relationship"
            )

            explanation = item.get(
                "explanation",
                ""
            )

            variables = item.get(
                "variables",
                ""
            )

            st.markdown(
                f"""
                <div class="reasoning-box">
                    <h4>🔗 {relationship}</h4>
                    <p>{explanation}</p>
                    <small>
                        <b>Variables:</b> {variables}
                    </small>
                </div>
                """,
                unsafe_allow_html=True
            )

    elif len(groups) >= 3:

        st.success(
            "Multiple environmental variable groups are "
            "available for cross-variable reasoning."
        )

    else:

        st.info(
            "More environmental variables may be required "
            "for cross-variable reasoning."
        )

    # ========================================================
    # 2. CLARIFYING QUESTIONS
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        "2. Clarifying Questions"
        "</div>",
        unsafe_allow_html=True
    )

    if missing:

        st.warning(
            "The environmental profile may need "
            "additional information."
        )

        if isinstance(
            missing,
            (list, tuple)
        ):

            for item in missing:

                st.write(
                    f"• {item}"
                )

        else:

            st.write(
                missing
            )

    else:

        st.success(
            "The available environmental profile contains "
            "the required fields for the current analysis."
        )

    # ========================================================
    # 3. RETRIEVED KNOWLEDGE
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        "3. Retrieved Knowledge"
        "</div>",
        unsafe_allow_html=True
    )

    st.caption(
        "Evidence retrieved from the local knowledge layer."
    )

    if retrieved:

        for index, item in enumerate(
            retrieved,
            start=1
        ):

            with st.expander(
                f"📚 Evidence {index}"
            ):

                if isinstance(
                    item,
                    dict
                ):

                    source = (
                        item.get("source")
                        or item.get("file")
                        or item.get(
                            "metadata",
                            {}
                        ).get(
                            "source"
                        )
                        or "Local knowledge"
                    )

                    text = (
                        item.get("text")
                        or item.get("content")
                        or item.get("page_content")
                        or str(item)
                    )

                    st.markdown(
                        f"**Source:** {source}"
                    )

                    st.write(
                        text
                    )

                else:

                    st.write(
                        str(item)
                    )

    else:

        st.info(
            "No retrieved evidence was returned "
            "by the knowledge layer."
        )

    # ========================================================
    # 4. EVIDENCE-BACKED RECOMMENDATION
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        "4. Evidence-Backed Recommendation"
        "</div>",
        unsafe_allow_html=True
    )

    if recommendations:

        for index, rec in enumerate(
            recommendations,
            start=1
        ):

            st.markdown(
                f"### 🌱 Recommendation {index}"
            )

            st.write(
                "**Recommendation:**",
                rec.get(
                    "recommendation",
                    ""
                )
            )

            st.write(
                "**Why it works:**",
                rec.get(
                    "why",
                    ""
                )
            )

            st.write(
                "**Impacted metrics:**",
                rec.get(
                    "metrics",
                    ""
                )
            )

            st.write(
                "**Expected measurable improvement:**",
                rec.get(
                    "expected_improvement",
                    "No quantitative estimate available "
                    "from the retrieved evidence."
                )
            )

            st.write(
                "**Time horizon:**",
                rec.get(
                    "time",
                    ""
                )
            )

            st.write(
                "**Confidence:**",
                rec.get(
                    "confidence",
                    ""
                )
            )

            st.write(
                "**Reference:**",
                rec.get(
                    "evidence",
                    ""
                )
            )

            scientific_references = rec.get(
                "scientific_references",
                []
            )

            if scientific_references:

                st.markdown(
                    "### 📚 Scientific References"
                )

                for ref in scientific_references:

                    st.markdown(
                        f"**{ref.get('source', 'Scientific source')}**"
                    )

                    st.write(
                        ref.get(
                            "finding",
                            ""
                        )
                    )

                    url = ref.get(
                        "url",
                        ""
                    )

                    if url:

                        st.markdown(
                            f"[View source]({url})"
                        )

    else:

        st.info(
            "No recommendation was generated."
        )

    # ========================================================
    # 5. SCIENTIST MEMORY
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        "5. Scientist Memory"
        "</div>",
        unsafe_allow_html=True
    )

    st.write(
        "Environmental analyses in this session"
    )

    st.metric(
        "Analyses",
        len(
            st.session_state.analysis_history
        )
    )

    with st.expander(
        "💬 View previous environmental context"
    ):

        if st.session_state.environmental_memory:

            for key, value in (
                st.session_state.environmental_memory.items()
            ):

                st.markdown(
                    f"**{key}:** {value}"
                )

        else:

            st.write(
                "No previous environmental context."
            )

    # --------------------------------------------------------
    # Analysis history
    # --------------------------------------------------------

    if st.session_state.analysis_history:

        with st.expander(
            "🗂️ View previous analyses"
        ):

            for index, item in enumerate(
                st.session_state.analysis_history,
                start=1
            ):

                st.markdown(
                    f"**Analysis {index}**"
                )

                if item.get("query"):

                    st.write(
                        "User input:",
                        item["query"]
                    )

                context = item.get(
                    "context",
                    {}
                )

                if context:

                    st.write(
                        "Environmental context:",
                        context
                    )

                st.markdown("---")


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Environmental Scientist • Biodiversity Intelligence • "
    "Knowledge Retrieval • Multi-Metric Reasoning"
)