import json
import os
from datetime import datetime

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="PolicyPulse",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = os.getenv("POLICY_PULSE_BACKEND_URL", "http://127.0.0.1:8000")

st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { background-color: #ffffff; }

/* Top bar */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.8rem 0;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 1.2rem;
}
.logo {
    font-size: 1.4rem;
    font-weight: 700;
    color: #1e293b;
    letter-spacing: -0.02em;
}
.logo span {
    color: #2563eb;
}

/* Climate bar */
.climate-bar {
    background: #f0f4ff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #2563eb;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    font-size: 1rem;
    color: #334155;
    line-height: 1.7;
}
.climate-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2563eb;
    margin-bottom: 0.4rem;
}

/* Intelligence cards */
.card-high {
    background: #f8fafc;
    border: 1px solid #fecaca;
    border-top: 3px solid #dc2626;
    border-radius: 8px;
    padding: 1rem;
    cursor: pointer;
    min-height: 140px;
}
.card-medium {
    background: #f8fafc;
    border: 1px solid #fde68a;
    border-top: 3px solid #d97706;
    border-radius: 8px;
    padding: 1rem;
    cursor: pointer;
    min-height: 140px;
}
.card-low {
    background: #f8fafc;
    border: 1px solid #bbf7d0;
    border-top: 3px solid #16a34a;
    border-radius: 8px;
    padding: 1rem;
    cursor: pointer;
    min-height: 140px;
}
.card-urgency {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.urgency-high { color: #dc2626; }
.urgency-medium { color: #d97706; }
.urgency-low { color: #16a34a; }
.card-visa {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 0.3rem;
}
.card-topic-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-bottom: 0.3rem;
}
.card-topic {
    font-size: 0.92rem;
    color: #64748b;
    line-height: 1.5;
}
.card-button-row {
    margin-top: 1rem;
}

/* Expanded panel */
.expand-panel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.5rem;
    margin-top: 1rem;
}
.expand-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #2563eb;
    margin-bottom: 0.5rem;
}
.expand-text {
    font-size: 1rem;
    color: #334155;
    line-height: 1.8;
}
.headline-large {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 0.75rem;
    line-height: 1.5;
}

/* Generated paragraph */
.gen-para {
    background: #eff6ff;
    border-left: 3px solid #2563eb;
    border-radius: 0 8px 8px 0;
    padding: 1.2rem 1.5rem;
    margin-top: 1rem;
    font-size: 1rem;
    color: #1e293b;
    line-height: 1.8;
    font-style: italic;
}

/* Action items */
.action-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #e2e8f0;
    font-size: 0.95rem;
    color: #64748b;
}
.action-number {
    color: #2563eb;
    font-weight: 700;
    min-width: 1.5rem;
}

/* Metadata row */
.meta-row {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 1.2rem;
    display: flex;
    gap: 1.5rem;
}

.section-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
    margin: 1.5rem 0 0.8rem 0;
}
</style>
""",
    unsafe_allow_html=True,
)

NATIONAL_ORIGIN_OPTIONS = [
    "All Origins",
    "India",
    "China",
    "Mexico",
    "Philippines",
    "Dominican Republic",
    "Afghanistan",
    "Albania",
    "Algeria",
    "Argentina",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bangladesh",
    "Belgium",
    "Bolivia",
    "Brazil",
    "Cambodia",
    "Canada",
    "Chile",
    "Colombia",
    "Costa Rica",
    "Cuba",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Ethiopia",
    "France",
    "Germany",
    "Ghana",
    "Guatemala",
    "Haiti",
    "Honduras",
    "Hong Kong",
    "Hungary",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "South Korea",
    "Lebanon",
    "Malaysia",
    "Morocco",
    "Nepal",
    "Netherlands",
    "Nicaragua",
    "Nigeria",
    "Pakistan",
    "Panama",
    "Peru",
    "Poland",
    "Portugal",
    "Romania",
    "Russia",
    "Saudi Arabia",
    "Senegal",
    "South Africa",
    "Spain",
    "Sri Lanka",
    "Syria",
    "Taiwan",
    "Thailand",
    "Trinidad and Tobago",
    "Turkey",
    "Ukraine",
    "United Kingdom",
    "Venezuela",
    "Vietnam",
    "Yemen",
    "Zimbabwe",
]

PERIOD_OPTIONS = [
    "June 2026",
    "May 2026",
    "April 2026",
    "March 2026",
    "February 2026",
    "January 2026",
    "December 2025",
    "November 2025",
    "October 2025",
]


def get_brief(period=None, visa_type=None, national_origin=None) -> dict:
    try:
        params = {}
        if visa_type and visa_type != "All":
            params["practice_areas"] = visa_type
        if national_origin and national_origin != "All Origins":
            params["client_nationalities"] = national_origin
        if period:
            params["active_concern"] = f"Focus on {period} regulatory updates"
        response = httpx.get(
            f"{BACKEND_URL}/retrieve/brief", params=params, timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


def get_sources() -> list:
    try:
        response = httpx.get(f"{BACKEND_URL}/retrieve/sources", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def trigger_all(sources) -> list:
    results = []
    for source in sources:
        try:
            response = httpx.post(
                f"{BACKEND_URL}/retrieve/{source['source_type']}", timeout=30
            )
            response.raise_for_status()
            results.append(
                {
                    "source": source["source_name"],
                    "ok": True,
                    "change": response.json().get("change_type", ""),
                }
            )
        except Exception:
            results.append({"source": source["source_name"], "ok": False})
    return results


def generate_paragraph(headline: str, context: str, visa: str, origin: str) -> str:
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "ANTHROPIC_API_KEY not configured."

        prompt = f"""You are a senior regulatory intelligence analyst and immigration law specialist.

An immigration attorney needs concise filing context bullets for their client file.

REGULATORY INTELLIGENCE:
Headline: {headline}
Visa Category: {visa}
National Origin: {origin}
Regulatory Context: {context[:1200]}

Format the output as 5-7 concise bullet points, each 1-2 sentences maximum.
Each bullet point should cover ONE specific fact or action item.
Use this structure:
- [Key regulatory fact with specific date/magnitude]
- [Who is affected and how]
- [Filing eligibility determination]
- [Filing methodology note]
- [Federal Register status]
- [Immediate action required]
- [Monitoring recommendation]

Start each bullet with •
No markdown headers.
No dense paragraphs.
Keep each bullet under 40 words.

Requirements:
- Formal legal correspondence register
- Specific and analytical — not generic
- Ground every statement in the provided regulatory content
- Include specific dates, percentages, or movements where available
- Do not provide legal advice or legal conclusions
- Do not fabricate information not present in the source
- Write as regulatory intelligence briefing, not legal opinion
"""

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=45,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    except Exception as exc:
        return f"Unable to generate paragraph: {exc}"


def backend_available() -> bool:
    try:
        response = httpx.get(f"{BACKEND_URL}/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def format_timestamp(value: str) -> str:
    if not value:
        return "—"
    try:
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except ValueError:
        return value


def card_classes(urgency: str) -> tuple[str, str]:
    urgency_value = (urgency or "Low").strip()
    card_map = {
        "High": ("card-high", "urgency-high"),
        "Medium": ("card-medium", "urgency-medium"),
    }
    return card_map.get(urgency_value, ("card-low", "urgency-low")) + (urgency_value,)


def render_topic_card(topic: dict) -> str:
    card_class, urgency_class, urgency_label = card_classes(topic.get("urgency", "Low"))
    visa_cat = topic.get("visa_category", "Unknown")
    parts = visa_cat.split(" — ", 1)
    main_cat = parts[0]
    descriptor = parts[1] if len(parts) > 1 else ""
    topic_text = topic.get("topic", "")
    descriptor_html = ""
    if descriptor:
        descriptor_html = f'  <div class="card-topic-label">{descriptor}</div>\n'
    return f"""
<div class="{card_class}">
  <div class="card-urgency {urgency_class}">{urgency_label} Priority</div>
  <div class="card-visa">{main_cat}</div>
{descriptor_html}  <div class="card-topic">{topic_text}</div>
</div>
"""


# Session state
if "selected_topic_idx" not in st.session_state:
    st.session_state.selected_topic_idx = None
if "generated_paragraph" not in st.session_state:
    st.session_state.generated_paragraph = ""
if "brief" not in st.session_state:
    st.session_state.brief = {}

# Top bar
st.markdown(
    """
<div class="top-bar">
  <div class="logo">Policy<span>Pulse</span></div>
</div>
""",
    unsafe_allow_html=True,
)

if not backend_available():
    st.warning(
        f"Backend unavailable at `{BACKEND_URL}`. "
        "Start the API with `uvicorn main:app --reload`."
    )

filter_col1, filter_col2, filter_col3, col_refresh = st.columns([2, 2, 2, 1])

with filter_col1:
    period = st.selectbox(
        "Period",
        PERIOD_OPTIONS,
        label_visibility="collapsed",
    )
with filter_col2:
    visa_type = st.selectbox(
        "Visa Type",
        ["All", "H-1B", "O-1", "EB-1", "EB-2", "EB-3", "L-1", "TN", "E-2", "K-1", "Family-based"],
        label_visibility="collapsed",
    )
with filter_col3:
    national_origin = st.selectbox(
        "National Origin",
        NATIONAL_ORIGIN_OPTIONS,
        label_visibility="collapsed",
    )
with col_refresh:
    generate = st.button(
        "Generate Report",
        use_container_width=True,
        type="primary",
        help="Retrieve latest regulatory data and generate intelligence report",
    )

visa_param = visa_type if visa_type != "All" else None
origin_param = national_origin if national_origin != "All Origins" else None

if generate:
    st.session_state.selected_topic_idx = None
    st.session_state.generated_paragraph = ""

if (
    "brief" not in st.session_state
    or not st.session_state.get("brief")
    or generate
    or st.session_state.get("last_visa") != visa_type
    or st.session_state.get("last_origin") != national_origin
    or st.session_state.get("last_period") != period
):
    if generate:
        with st.spinner("Retrieving regulatory data and generating report..."):
            sources = get_sources()
            trigger_all(sources)
            brief = get_brief(period, visa_param, origin_param)
    else:
        brief = get_brief(period, visa_param, origin_param)

    st.session_state.brief = brief
    st.session_state.last_visa = visa_type
    st.session_state.last_origin = national_origin
    st.session_state.last_period = period
else:
    brief = st.session_state.brief

if not brief:
    st.info("No brief available. Click Generate Report or check backend connection.")
    st.stop()

climate = brief.get("climate") or "No regulatory climate summary available."
st.markdown(
    f"""
<div class="climate-bar">
  <div class="climate-label">Regulatory Climate</div>
  {climate}
</div>
""",
    unsafe_allow_html=True,
)

generated_at = format_timestamp(brief.get("generated_at", ""))
source_count = brief.get("source_count", 0)
st.markdown(
    f"""
<div class="meta-row">
  <span>Generated {generated_at}</span>
  <span>{source_count} sources analyzed</span>
  <span>Filter: {visa_type} · {national_origin} · {period}</span>
</div>
""",
    unsafe_allow_html=True,
)

topics = brief.get("active_topics") or []
st.markdown('<div class="section-title">Intelligence Feed</div>', unsafe_allow_html=True)

st.markdown(
    """
<div style="display:flex; gap:1.5rem; margin-bottom:1rem;
     font-size:0.78rem;">
    <span>
        <span style="color:#dc2626; font-weight:700;">● HIGH</span>
        <span style="color:#64748b;"> — Act this month</span>
    </span>
    <span>
        <span style="color:#d97706; font-weight:700;">● MEDIUM</span>
        <span style="color:#64748b;"> — Monitor closely</span>
    </span>
    <span>
        <span style="color:#16a34a; font-weight:700;">● LOW</span>
        <span style="color:#64748b;"> — Positive or stable</span>
    </span>
</div>
""",
    unsafe_allow_html=True,
)

if not topics:
    st.markdown(
        '<div class="expand-text">No active topics identified for current filters.</div>',
        unsafe_allow_html=True,
    )
else:
    cols = st.columns(3)
    for index, topic in enumerate(topics):
        with cols[index % 3]:
            st.markdown(render_topic_card(topic), unsafe_allow_html=True)
            st.markdown('<div class="card-button-row"></div>', unsafe_allow_html=True)
            if st.button("Analyze →", key=f"topic_btn_{index}", use_container_width=True):
                st.session_state.selected_topic_idx = index
                st.session_state.generated_paragraph = ""
                st.rerun()

if st.session_state.selected_topic_idx is not None and topics:
    selected = topics[st.session_state.selected_topic_idx]
    headline = selected.get("topic", "")
    visa = selected.get("visa_category", visa_type)
    context = "\n".join(
        filter(
            None,
            [
                brief.get("federal_register_summary"),
                brief.get("visa_bulletin_status"),
                brief.get("climate"),
            ],
        )
    )

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.markdown(
            '<div class="expand-panel">'
            '<div class="expand-label">Topic Analysis</div>'
            f'<div class="headline-large">{headline}</div>'
            f'<div class="expand-text">{brief.get("visa_bulletin_status", "") or "—"}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        fr_col, vb_col = st.columns(2)
        with fr_col:
            st.markdown(
                '<div class="expand-label">Federal Register</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="expand-text">{brief.get("federal_register_summary") or "—"}</div>',
                unsafe_allow_html=True,
            )
        with vb_col:
            st.markdown(
                '<div class="expand-label">Visa Bulletin</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="expand-text">{brief.get("visa_bulletin_status") or "—"}</div>',
                unsafe_allow_html=True,
            )

    with right_col:
        st.markdown(
            '<div class="expand-label">Filing Context Paragraph</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.generated_paragraph:
            st.markdown(
                f"""
<div class="gen-para">
  {st.session_state.generated_paragraph}
</div>
""",
                unsafe_allow_html=True,
            )
            st.download_button(
                label="Download Filing Context",
                data=st.session_state.generated_paragraph,
                file_name="filing_context.txt",
                mime="text/plain",
                use_container_width=True,
            )
        else:
            st.markdown(
                """
<div style="
    border: 2px dashed #e2e8f0;
    border-radius: 8px;
    padding: 2rem;
    text-align: center;
    color: #94a3b8;
    font-size: 0.9rem;
    min-height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
">
    <div>
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">✍️</div>
        <div style="font-weight: 600; color: #64748b;">Filing Context Paragraph</div>
        <div style="margin-top: 0.3rem;">Click "Generate Filing Context" to create<br>
        a regulatory paragraph for this matter</div>
    </div>
</div>
""",
                unsafe_allow_html=True,
            )

        if st.button("Generate Filing Context", key="gen_para_btn", use_container_width=True):
            with st.spinner("Generating filing context..."):
                st.session_state.generated_paragraph = generate_paragraph(
                    headline=headline,
                    context=context,
                    visa=visa if visa != "All" else visa_type,
                    origin=national_origin
                    if national_origin != "All Origins"
                    else "all nationalities",
                )
                st.rerun()

st.markdown('<div class="section-title">Attorney Action Items</div>', unsafe_allow_html=True)
action_items = brief.get("attorney_action_items") or []
if not action_items:
    st.markdown(
        '<div class="expand-text">No action items for current filters.</div>',
        unsafe_allow_html=True,
    )
else:
    for index, item in enumerate(action_items, start=1):
        st.markdown(
            f"""
<div class="action-item">
  <span class="action-number">{index}.</span>
  <span>{item}</span>
</div>
""",
            unsafe_allow_html=True,
        )

if brief.get("sources_cited"):
    st.markdown(
        """
    <div style="margin-top:1.5rem; padding-top:1rem;
         border-top:1px solid #e2e8f0;">
    <div style="font-size:0.72rem; font-weight:700;
         letter-spacing:0.1em; text-transform:uppercase;
         color:#64748b; margin-bottom:0.5rem;">
    Sources
    </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    for source in brief.get("sources_cited", []):
        name = source.get("name", "")
        date = source.get("date", "")
        url = source.get("url", "")
        if url:
            st.markdown(
                f'<div style="font-size:0.82rem; color:#64748b; '
                f'padding:0.2rem 0;">📄 '
                f'<a href="{url}" target="_blank" '
                f'style="color:#2563eb;">{name}</a>'
                f'{" — " + date if date else ""}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-size:0.82rem; color:#64748b; '
                f'padding:0.2rem 0;">📄 {name}'
                f'{" — " + date if date else ""}</div>',
                unsafe_allow_html=True,
            )
