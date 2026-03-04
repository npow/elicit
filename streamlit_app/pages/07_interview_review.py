"""Interview Review page -- post-interview quality scoring."""

import streamlit as st
import httpx

st.set_page_config(page_title="Interview Review", layout="wide")

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


def _score_color(score: float) -> str:
    """Return a color based on score value (0-1)."""
    if score >= 0.8:
        return "normal"
    if score >= 0.5:
        return "off"
    return "inverse"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Interview Review")
st.markdown("Score your interviews for **Mom Test** compliance, question quality, and bias.")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Fetch interviews
# ---------------------------------------------------------------------------

try:
    resp = _api("get", f"/interviews/{project_id}")
    resp.raise_for_status()
    interviews = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load interviews: {exc}")
    interviews = []

if not interviews:
    st.info("No interviews in this project. Upload one on the **Upload** page first.")
    st.stop()

# ---------------------------------------------------------------------------
# Select interview
# ---------------------------------------------------------------------------

interview_map = {iv["id"]: f"{iv['title'] or 'Untitled'} -- {iv['interviewee_name'] or 'Unknown'}" for iv in interviews}

selected_iv_id = st.selectbox(
    "Select an Interview to Review",
    options=list(interview_map.keys()),
    format_func=lambda iid: interview_map[iid],
)

if not selected_iv_id:
    st.stop()

# ---------------------------------------------------------------------------
# Score button
# ---------------------------------------------------------------------------

if st.button("Score This Interview"):
    with st.spinner("Analyzing interview quality ..."):
        try:
            resp = _api("post", f"/coaching/score/{selected_iv_id}")
            resp.raise_for_status()
            st.success("Scoring complete!")
            st.rerun()
        except httpx.HTTPError as exc:
            st.error(f"Scoring failed: {exc}")

# ---------------------------------------------------------------------------
# Fetch existing scores
# ---------------------------------------------------------------------------

try:
    resp = _api("get", f"/coaching/scores/{selected_iv_id}")
    resp.raise_for_status()
    scores_list = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load scores: {exc}")
    scores_list = []

if not scores_list:
    st.info("No quality scores yet. Click **Score This Interview** to generate one.")
    st.stop()

# Show the most recent score
score = scores_list[0]

st.divider()
st.subheader("Quality Scores")

# ---------------------------------------------------------------------------
# Visual gauges with st.metric and st.progress_bar
# ---------------------------------------------------------------------------

gauge_cols = st.columns(5)

overall = score.get("overall_score", 0)
mom_test = score.get("mom_test_compliance", 0)
q_quality = score.get("question_quality", 0)
insight = score.get("insight_depth", 0)
bias = score.get("bias_score", 0)

with gauge_cols[0]:
    st.metric("Overall Score", f"{int(overall * 100)}%", delta_color=_score_color(overall))
    st.progress(overall)

with gauge_cols[1]:
    st.metric("Mom Test Compliance", f"{int(mom_test * 100)}%", delta_color=_score_color(mom_test))
    st.progress(mom_test)

with gauge_cols[2]:
    st.metric("Question Quality", f"{int(q_quality * 100)}%", delta_color=_score_color(q_quality))
    st.progress(q_quality)

with gauge_cols[3]:
    st.metric("Insight Depth", f"{int(insight * 100)}%", delta_color=_score_color(insight))
    st.progress(insight)

with gauge_cols[4]:
    # Lower bias is better, so invert the visual cue
    bias_label = "Low" if bias < 0.3 else "Medium" if bias < 0.6 else "High"
    st.metric("Bias Score", f"{int(bias * 100)}% ({bias_label})")
    st.progress(bias)

st.divider()

# ---------------------------------------------------------------------------
# Detailed findings
# ---------------------------------------------------------------------------

detail_col_left, detail_col_right = st.columns(2)

with detail_col_left:
    # Leading questions
    st.markdown("**Leading Questions Found**")
    leading_qs = score.get("leading_questions_found", [])
    if leading_qs:
        for lq in leading_qs:
            if isinstance(lq, dict):
                question = lq.get("question") or lq.get("text") or str(lq)
                explanation = lq.get("explanation") or lq.get("reason") or ""
                st.markdown(f"- {question}")
                if explanation:
                    st.caption(f"  {explanation}")
            else:
                st.markdown(f"- {lq}")
    else:
        st.success("No leading questions detected.")

    # Missed opportunities
    st.markdown("**Missed Opportunities**")
    missed = score.get("missed_opportunities", [])
    if missed:
        for mo in missed:
            if isinstance(mo, dict):
                desc = mo.get("description") or mo.get("text") or str(mo)
                suggestion = mo.get("suggestion") or ""
                st.markdown(f"- {desc}")
                if suggestion:
                    st.caption(f"  Suggestion: {suggestion}")
            else:
                st.markdown(f"- {mo}")
    else:
        st.success("No missed opportunities identified.")

with detail_col_right:
    # Strengths
    st.markdown("**Strengths**")
    strengths = score.get("strengths", [])
    if strengths:
        for s in strengths:
            st.markdown(f"- {s}")
    else:
        st.caption("None noted.")

    # Suggestions
    st.markdown("**Suggestions for Improvement**")
    suggestions = score.get("suggestions", [])
    if suggestions:
        for s in suggestions:
            st.markdown(f"- {s}")
    else:
        st.caption("None provided.")

# ---------------------------------------------------------------------------
# Score history
# ---------------------------------------------------------------------------

if len(scores_list) > 1:
    st.divider()
    with st.expander(f"Previous Scores ({len(scores_list) - 1} older)"):
        for older in scores_list[1:]:
            created = older.get("created_at", "")[:19] if older.get("created_at") else "N/A"
            st.markdown(
                f"- **{created}** -- Overall: {int(older.get('overall_score', 0) * 100)}% "
                f"| Mom Test: {int(older.get('mom_test_compliance', 0) * 100)}% "
                f"| Bias: {int(older.get('bias_score', 0) * 100)}%"
            )
