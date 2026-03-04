"""Interview Prep page -- generate Mom Test interview guides."""

import streamlit as st
import httpx

st.set_page_config(page_title="Interview Prep", layout="wide")

API_BASE = st.session_state.get("api_base", "http://localhost:8000/api")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=60.0) as client:
        return getattr(client, method)(url, **kwargs)


def _require_project() -> str:
    pid = st.session_state.get("project_id")
    if not pid:
        st.warning("Please select a project on the **Projects** page first.")
        st.stop()
    return pid


def _render_questions(questions: list, header: str) -> None:
    """Render a list of question dicts (or strings)."""
    st.markdown(f"**{header}**")
    if not questions:
        st.caption("None provided.")
        return
    for i, q in enumerate(questions, start=1):
        if isinstance(q, dict):
            question_text = q.get("question") or q.get("text") or str(q)
            purpose = q.get("purpose") or q.get("rationale") or ""
            st.markdown(f"{i}. {question_text}")
            if purpose:
                st.caption(f"   Purpose: {purpose}")
        else:
            st.markdown(f"{i}. {q}")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Interview Prep")
st.markdown("Generate **Mom Test** interview guides to avoid leading questions and extract real insights.")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Generate guide form
# ---------------------------------------------------------------------------

with st.form("generate_guide_form"):
    hypothesis = st.text_area(
        "Hypothesis *",
        placeholder="e.g. Product managers at mid-size SaaS companies spend >3 hrs/week manually creating roadmaps",
    )
    target_persona = st.text_input(
        "Target Persona *",
        placeholder="e.g. Product Manager at a 100-500 person B2B SaaS company",
    )
    existing_insights = st.text_area(
        "Existing Insights (optional)",
        height=120,
        placeholder="Paste any prior interview notes or known context to help the AI generate better questions ...",
    )
    generate_btn = st.form_submit_button("Generate Guide")

if generate_btn:
    if not hypothesis.strip() or not target_persona.strip():
        st.warning("Both hypothesis and target persona are required.")
    else:
        with st.spinner("Generating Mom Test interview guide ..."):
            try:
                resp = _api(
                    "post",
                    f"/coaching/guide/{project_id}",
                    json={
                        "hypothesis": hypothesis.strip(),
                        "target_persona": target_persona.strip(),
                        "existing_insights": existing_insights.strip(),
                    },
                )
                resp.raise_for_status()
                st.success("Guide generated!")
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Guide generation failed: {exc}")

# ---------------------------------------------------------------------------
# List previous guides
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Interview Guides")

try:
    resp = _api("get", f"/coaching/guides/{project_id}")
    resp.raise_for_status()
    guides = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to fetch guides: {exc}")
    guides = []

if not guides:
    st.info("No guides yet. Generate one above.")
    st.stop()

# ---------------------------------------------------------------------------
# Display each guide
# ---------------------------------------------------------------------------

for guide in guides:
    title = guide.get("title") or f"Guide for {guide.get('target_persona', 'Unknown')}"
    created = guide.get("created_at", "")[:10] if guide.get("created_at") else ""

    with st.expander(f"{title}  ({created})", expanded=(guide == guides[0])):
        st.markdown(f"**Hypothesis:** {guide.get('hypothesis', 'N/A')}")
        st.markdown(f"**Target Persona:** {guide.get('target_persona', 'N/A')}")

        if guide.get("success_criteria"):
            st.markdown(f"**Success Criteria:** {guide['success_criteria']}")

        st.divider()

        # Questions in columns
        q_col1, q_col2, q_col3 = st.columns(3)

        with q_col1:
            _render_questions(guide.get("opening_questions", []), "Opening Questions")

        with q_col2:
            _render_questions(guide.get("deep_dive_questions", []), "Deep Dive Questions")

        with q_col3:
            _render_questions(guide.get("validation_questions", []), "Validation Questions")

        # Anti-patterns
        st.divider()
        st.markdown("**Anti-Patterns to Avoid**")
        anti_patterns = guide.get("anti_patterns_to_avoid", [])
        if anti_patterns:
            for ap in anti_patterns:
                st.markdown(f"- {ap}")
        else:
            st.caption("None listed.")
