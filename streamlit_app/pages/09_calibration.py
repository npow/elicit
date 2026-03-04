"""Calibration page -- compare synthetic persona predictions against real interviews."""

import streamlit as st
import httpx
import pandas as pd

st.set_page_config(page_title="Calibration", layout="wide")

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


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Calibration Dashboard")
st.markdown("Compare **synthetic persona** predictions against **real interview** data to track accuracy.")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Fetch personas and interviews for selection
# ---------------------------------------------------------------------------

try:
    resp = _api("get", f"/simulation/personas/{project_id}")
    resp.raise_for_status()
    personas = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load personas: {exc}")
    personas = []

try:
    resp = _api("get", f"/interviews/{project_id}")
    resp.raise_for_status()
    interviews = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load interviews: {exc}")
    interviews = []

if not personas:
    st.info("No synthetic personas found. Generate some on the **Simulator** page first.")
    st.stop()

if not interviews:
    st.info("No real interviews found. Upload one on the **Upload** page first.")
    st.stop()

# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

st.subheader("Run Calibration")

sel_cols = st.columns(2)

with sel_cols[0]:
    persona_map = {p["id"]: f"{p['name']} -- {p['role']}" for p in personas}
    selected_persona_id = st.selectbox(
        "Select Persona",
        options=list(persona_map.keys()),
        format_func=lambda pid: persona_map[pid],
    )

with sel_cols[1]:
    interview_map = {iv["id"]: f"{iv['title'] or 'Untitled'} -- {iv['interviewee_name'] or 'Unknown'}" for iv in interviews}
    selected_interview_id = st.selectbox(
        "Select Real Interview",
        options=list(interview_map.keys()),
        format_func=lambda iid: interview_map[iid],
    )

# ---------------------------------------------------------------------------
# Run calibration
# ---------------------------------------------------------------------------

if st.button("Run Calibration"):
    if not selected_persona_id or not selected_interview_id:
        st.warning("Please select both a persona and an interview.")
    else:
        with st.spinner("Running calibration comparison ..."):
            try:
                resp = _api(
                    "post",
                    f"/calibration/{project_id}",
                    json={
                        "persona_id": selected_persona_id,
                        "interview_id": selected_interview_id,
                    },
                )
                resp.raise_for_status()
                result = resp.json()

                st.success("Calibration complete!")

                # Display overlap scores as metrics
                st.divider()
                st.subheader("Overlap Scores")

                metric_cols = st.columns(4)
                with metric_cols[0]:
                    overall = result.get("overall_accuracy", 0)
                    st.metric("Overall Accuracy", f"{int(overall * 100)}%")
                    st.progress(overall)

                with metric_cols[1]:
                    job_overlap = result.get("job_overlap_score", 0)
                    st.metric("Job Overlap", f"{int(job_overlap * 100)}%")
                    st.progress(job_overlap)

                with metric_cols[2]:
                    pain_overlap = result.get("pain_overlap_score", 0)
                    st.metric("Pain Overlap", f"{int(pain_overlap * 100)}%")
                    st.progress(pain_overlap)

                with metric_cols[3]:
                    wa_overlap = result.get("workaround_overlap_score", 0)
                    st.metric("Workaround Overlap", f"{int(wa_overlap * 100)}%")
                    st.progress(wa_overlap)

                if result.get("notes"):
                    st.markdown(f"**Notes:** {result['notes']}")

            except httpx.HTTPError as exc:
                st.error(f"Calibration failed: {exc}")

# ---------------------------------------------------------------------------
# Accuracy trend chart
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Accuracy Trend")

try:
    resp = _api("get", f"/calibration/accuracy/{project_id}")
    resp.raise_for_status()
    trend_data = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load accuracy trend: {exc}")
    trend_data = None

if not trend_data:
    st.info("No calibration history yet. Run a calibration above to start tracking accuracy over time.")
else:
    # The trend data may be a list of records with timestamps and scores
    if isinstance(trend_data, list) and len(trend_data) > 0:
        # Build a DataFrame for charting
        records = []
        for entry in trend_data:
            record = {}
            # Handle different possible key names
            record["date"] = (
                entry.get("created_at")
                or entry.get("timestamp")
                or entry.get("date")
                or ""
            )
            record["Overall Accuracy"] = entry.get("overall_accuracy", 0)
            record["Job Overlap"] = entry.get("job_overlap_score", 0)
            record["Pain Overlap"] = entry.get("pain_overlap_score", 0)
            record["Workaround Overlap"] = entry.get("workaround_overlap_score", 0)
            records.append(record)

        df = pd.DataFrame(records)

        # Try to parse dates for a proper time axis
        if df["date"].any():
            try:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
            except Exception:
                df = df.drop(columns=["date"])
        else:
            df = df.drop(columns=["date"])

        st.line_chart(df)

        # Summary table
        with st.expander("Raw Data"):
            st.dataframe(df.reset_index() if "date" in df.index.names else df, use_container_width=True)
    elif isinstance(trend_data, dict):
        # Possibly a single summary object
        st.json(trend_data)
    else:
        st.info("No trend data available.")
