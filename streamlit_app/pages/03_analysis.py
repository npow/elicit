"""Analysis page -- view extracted insights and run cross-interview synthesis."""

import streamlit as st
import httpx
import time

st.set_page_config(page_title="Analysis", layout="wide")

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


def _render_confidence_bar(confidence: float) -> None:
    """Render a small confidence indicator."""
    pct = int(confidence * 100)
    st.progress(confidence, text=f"Confidence: {pct}%")


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


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Analysis")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Fetch interviews for this project
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
# Interview selector
# ---------------------------------------------------------------------------

interview_map = {iv["id"]: f"{iv['title'] or 'Untitled'} -- {iv['interviewee_name'] or 'Unknown'}" for iv in interviews}

selected_iv_id = st.selectbox(
    "Select an Interview",
    options=list(interview_map.keys()),
    format_func=lambda iid: interview_map[iid],
)

if not selected_iv_id:
    st.stop()

# ---------------------------------------------------------------------------
# Fetch extractions
# ---------------------------------------------------------------------------

try:
    resp = _api("get", f"/analysis/extractions/{selected_iv_id}")
    resp.raise_for_status()
    extractions = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load extractions: {exc}")
    extractions = {"jobs": [], "pain_points": [], "workarounds": [], "opportunities": []}

jobs = extractions.get("jobs", [])
pains = extractions.get("pain_points", [])
workarounds = extractions.get("workarounds", [])
opportunities = extractions.get("opportunities", [])

has_data = any([jobs, pains, workarounds, opportunities])

if not has_data:
    st.info("No extraction data yet. Run extraction from the **Upload** page first.")

# ---------------------------------------------------------------------------
# Extraction tabs
# ---------------------------------------------------------------------------

tab_jobs, tab_pains, tab_workarounds, tab_opps = st.tabs([
    f"Jobs ({len(jobs)})",
    f"Pain Points ({len(pains)})",
    f"Workarounds ({len(workarounds)})",
    f"Opportunities ({len(opportunities)})",
])

with tab_jobs:
    if not jobs:
        st.info("No jobs-to-be-done extracted.")
    for j in jobs:
        with st.container(border=True):
            st.markdown(f"**{j['statement']}**")
            if j.get("context"):
                st.caption(f"Context: {j['context']}")
            cols = st.columns(3)
            cols[0].write(f"Frequency: {j.get('frequency', 'N/A')}")
            cols[1].write(f"Importance: {j.get('importance', 'N/A')}")
            cols[2].write(f"Satisfaction: {j.get('satisfaction', 'N/A')}")
            if j.get("supporting_quote"):
                st.markdown(f"> *\"{j['supporting_quote']}\"*")
            _render_confidence_bar(j.get("confidence", 0.0))

with tab_pains:
    if not pains:
        st.info("No pain points extracted.")
    for p in pains:
        with st.container(border=True):
            st.markdown(f"**{p['description']}**")
            cols = st.columns(3)
            cols[0].write(f"Severity: {p.get('severity', 'N/A')}")
            cols[1].write(f"Frequency: {p.get('frequency', 'N/A')}")
            cols[2].write(f"Emotional Intensity: {p.get('emotional_intensity', 'N/A')}")
            if p.get("supporting_quote"):
                st.markdown(f"> *\"{p['supporting_quote']}\"*")
            _render_confidence_bar(p.get("confidence", 0.0))

with tab_workarounds:
    if not workarounds:
        st.info("No workarounds extracted.")
    for w in workarounds:
        with st.container(border=True):
            st.markdown(f"**{w['description']}**")
            cols = st.columns(3)
            cols[0].write(f"Tools: {w.get('tools_used', 'N/A')}")
            cols[1].write(f"Effort: {w.get('effort_level', 'N/A')}")
            cols[2].write(f"Satisfaction: {w.get('satisfaction_with_workaround', 'N/A')}")
            if w.get("supporting_quote"):
                st.markdown(f"> *\"{w['supporting_quote']}\"*")
            _render_confidence_bar(w.get("confidence", 0.0))

with tab_opps:
    if not opportunities:
        st.info("No opportunities extracted.")
    for o in opportunities:
        with st.container(border=True):
            st.markdown(f"**{o['description']}**")
            cols = st.columns(3)
            cols[0].metric("Opportunity Score", f"{o.get('opportunity_score', 0):.2f}")
            cols[1].metric("Importance", f"{o.get('importance_score', 0):.2f}")
            cols[2].metric("Satisfaction", f"{o.get('satisfaction_score', 0):.2f}")
            if o.get("market_size_indicator"):
                st.write(f"Market Size: {o['market_size_indicator']}")
            _render_confidence_bar(o.get("confidence", 0.0))

# ---------------------------------------------------------------------------
# Cross-interview synthesis
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Cross-Interview Synthesis")

if st.button("Run Synthesis Across All Interviews"):
    with st.spinner("Queueing synthesis ..."):
        try:
            resp = _api("post", f"/analysis/jobs/synthesize/{project_id}")
            resp.raise_for_status()
            job = resp.json()
            final = _wait_for_job(job["id"])
            if final.get("status") == "completed":
                result = final.get("result", {})
                st.success(f"Found **{result.get('patterns_count', 0)}** cross-interview patterns.")
                st.rerun()
            elif final.get("status") == "failed":
                st.error(f"Synthesis failed: {final.get('error_message', 'unknown error')}")
            else:
                st.info(f"Synthesis job queued: `{job['id']}` (still running)")
        except httpx.HTTPError as exc:
            st.error(f"Synthesis failed: {exc}")

# Fetch existing patterns
try:
    resp = _api("get", f"/analysis/patterns/{project_id}")
    resp.raise_for_status()
    patterns = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load patterns: {exc}")
    patterns = []

if not patterns:
    st.info("No cross-interview patterns yet. Run synthesis above after extracting multiple interviews.")
else:
    for pat in patterns:
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"**{pat['description']}**")
                st.caption(f"Type: {pat.get('pattern_type', 'N/A')} | Seen in {pat.get('frequency_count', 0)} interviews")
            with cols[1]:
                strength = pat.get("strength", 0.0)
                st.metric("Strength", f"{strength:.2f}")
            if pat.get("supporting_quotes"):
                with st.expander("Supporting Quotes"):
                    quotes = pat["supporting_quotes"]
                    if isinstance(quotes, list):
                        for q in quotes:
                            if isinstance(q, str):
                                st.markdown(f"> *\"{q}\"*")
                            elif isinstance(q, dict):
                                st.markdown(f"> *\"{q.get('quote', q)}\"*")
                    else:
                        st.write(quotes)
            _render_confidence_bar(pat.get("confidence", 0.0))
