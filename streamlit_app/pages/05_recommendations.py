"""Recommendations page -- prioritized 'Build This Next' dashboard."""

import streamlit as st
import httpx
import time

st.set_page_config(page_title="Recommendations", layout="wide")

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


def _wait_for_job(job_id: str, timeout_s: int = 120) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        resp = _api("get", f"/analysis/jobs/{job_id}")
        resp.raise_for_status()
        last = resp.json()
        if last.get("status") in {"completed", "failed"}:
            return last
        time.sleep(1.0)
    return last


CATEGORY_COLORS = {
    "must_have": "#E53935",
    "performance": "#FB8C00",
    "delighter": "#43A047",
    "table_stakes": "#1E88E5",
}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Recommendations")
st.markdown("Prioritized **Build This Next** insights derived from your interviews.")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Generate / refresh recommendations
# ---------------------------------------------------------------------------

if st.button("Generate / Refresh Recommendations"):
    with st.spinner("Queueing recommendation generation ..."):
        try:
            resp = _api("post", f"/analysis/jobs/recommend/{project_id}")
            resp.raise_for_status()
            job = resp.json()
            final = _wait_for_job(job["id"])
            if final.get("status") == "completed":
                result = final.get("result", {})
                st.success(f"Generated **{result.get('recommendations_count', 0)}** recommendations.")
                st.rerun()
            elif final.get("status") == "failed":
                st.error(f"Recommendation generation failed: {final.get('error_message', 'unknown error')}")
            else:
                st.info(f"Recommendation job queued: `{job['id']}` (still running)")
        except httpx.HTTPError as exc:
            st.error(f"Recommendation generation failed: {exc}")

# ---------------------------------------------------------------------------
# Fetch existing recommendations
# ---------------------------------------------------------------------------

try:
    resp = _api("get", f"/analysis/recommendations/{project_id}")
    resp.raise_for_status()
    recommendations = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to fetch recommendations: {exc}")
    recommendations = []

if not recommendations:
    st.info(
        "No recommendations yet. Run extraction and synthesis first, then generate recommendations above."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Sort by priority_rank
# ---------------------------------------------------------------------------

recommendations.sort(key=lambda r: r.get("priority_rank") or r.get("priority_score", 0))

# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

col_count, col_avg_score, col_top_cat = st.columns(3)
col_count.metric("Total Recommendations", len(recommendations))

scores = [r.get("priority_score", 0) for r in recommendations]
avg_score = sum(scores) / len(scores) if scores else 0
col_avg_score.metric("Avg Priority Score", f"{avg_score:.2f}")

categories = [r.get("category", "unknown") for r in recommendations]
if categories:
    top_cat = max(set(categories), key=categories.count)
    col_top_cat.metric("Top Category", top_cat.replace("_", " ").title())

st.divider()

# ---------------------------------------------------------------------------
# Recommendation cards
# ---------------------------------------------------------------------------

for rec in recommendations:
    rank = rec.get("priority_rank", "-")
    title = rec.get("title", "Untitled")
    desc = rec.get("description", "")
    priority_score = rec.get("priority_score", 0)
    category = rec.get("category", "")
    rationale = rec.get("rationale", "")
    risks = rec.get("risks", "")
    next_steps = rec.get("next_steps", "")
    confidence = rec.get("confidence", 0)
    evidence_chains = rec.get("evidence_chains", [])

    cat_color = CATEGORY_COLORS.get(category.lower(), "#757575")

    with st.container(border=True):
        # Header row
        header_cols = st.columns([1, 4, 2])
        with header_cols[0]:
            st.markdown(f"### #{rank}")
        with header_cols[1]:
            st.markdown(f"### {title}")
            st.markdown(
                f"<span style='color:{cat_color}; font-weight:bold;'>"
                f"{category.replace('_', ' ').upper()}</span>",
                unsafe_allow_html=True,
            )
        with header_cols[2]:
            st.metric("Priority Score", f"{priority_score:.2f}")
            st.progress(confidence, text=f"Confidence: {int(confidence * 100)}%")

        # Description
        if desc:
            st.markdown(f"**Description:** {desc}")

        # Detail columns
        detail_cols = st.columns(3)
        with detail_cols[0]:
            st.markdown("**Rationale**")
            st.write(rationale or "_Not provided._")
        with detail_cols[1]:
            st.markdown("**Risks**")
            st.write(risks or "_None identified._")
        with detail_cols[2]:
            st.markdown("**Next Steps**")
            st.write(next_steps or "_Not specified._")

        # Evidence chains
        if evidence_chains:
            with st.expander(f"Evidence Chain ({len(evidence_chains)} sources)"):
                for ev in evidence_chains:
                    with st.container(border=True):
                        ev_type = ev.get("evidence_type", "unknown")
                        quote = ev.get("quote", "")
                        relevance = ev.get("relevance_score", 0)
                        st.markdown(f"**Type:** {ev_type}  |  **Relevance:** {relevance:.2f}")
                        if quote:
                            st.markdown(f"> *\"{quote}\"*")
