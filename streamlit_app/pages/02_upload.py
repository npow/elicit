"""Upload page -- paste or upload interview transcripts for the active project."""

import streamlit as st
import httpx
import time

st.set_page_config(page_title="Upload Transcripts", layout="wide")

API_BASE = st.session_state.get("api_base", "http://localhost:8000/api")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=60.0) as client:
        return getattr(client, method)(url, **kwargs)


def _require_project() -> str:
    """Return the current project_id or stop the page with a warning."""
    pid = st.session_state.get("project_id")
    if not pid:
        st.warning("Please select a project on the **Projects** page first.")
        st.stop()
    return pid


def _wait_for_job(job_id: str, timeout_s: int = 90) -> dict:
    """Poll an analysis job until terminal state or timeout."""
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

st.title("Upload Transcripts")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Upload form -- paste text
# ---------------------------------------------------------------------------

tab_paste, tab_file = st.tabs(["Paste Transcript", "Upload File (.txt)"])

with tab_paste:
    with st.form("paste_form"):
        title = st.text_input("Interview Title", placeholder="e.g. Interview with Jane - Jan 2025")
        interviewee_name = st.text_input("Interviewee Name", placeholder="Jane Doe")
        interviewee_role = st.text_input("Interviewee Role", placeholder="Head of Product")
        transcript = st.text_area(
            "Transcript *",
            height=300,
            placeholder="Paste the full interview transcript here ...",
        )
        paste_submit = st.form_submit_button("Upload Transcript")

    if paste_submit:
        if not transcript.strip():
            st.warning("Transcript text is required.")
        else:
            try:
                resp = _api(
                    "post",
                    f"/interviews/{project_id}/text",
                    json={
                        "title": title.strip(),
                        "interviewee_name": interviewee_name.strip(),
                        "interviewee_role": interviewee_role.strip(),
                        "transcript": transcript.strip(),
                    },
                )
                resp.raise_for_status()
                interview = resp.json()
                st.success(f"Interview **{interview['title'] or interview['id']}** uploaded!")
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Upload failed: {exc}")

with tab_file:
    with st.form("file_form"):
        file_title = st.text_input("Interview Title", key="file_title", placeholder="e.g. Call with Bob")
        file_name = st.text_input("Interviewee Name", key="file_name", placeholder="Bob Smith")
        file_role = st.text_input("Interviewee Role", key="file_role", placeholder="VP Engineering")
        uploaded = st.file_uploader("Choose a .txt file", type=["txt"])
        file_submit = st.form_submit_button("Upload File")

    if file_submit:
        if uploaded is None:
            st.warning("Please choose a .txt file.")
        else:
            file_text = uploaded.read().decode("utf-8", errors="replace")
            if not file_text.strip():
                st.warning("The uploaded file is empty.")
            else:
                try:
                    resp = _api(
                        "post",
                        f"/interviews/{project_id}/text",
                        json={
                            "title": file_title.strip() or uploaded.name,
                            "interviewee_name": file_name.strip(),
                            "interviewee_role": file_role.strip(),
                            "transcript": file_text.strip(),
                        },
                    )
                    resp.raise_for_status()
                    interview = resp.json()
                    st.success(f"Interview **{interview['title'] or interview['id']}** uploaded!")
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Upload failed: {exc}")

# ---------------------------------------------------------------------------
# List existing interviews for this project
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Uploaded Interviews")

try:
    resp = _api("get", f"/interviews/{project_id}")
    resp.raise_for_status()
    interviews = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to fetch interviews: {exc}")
    interviews = []

if not interviews:
    st.info("No interviews yet. Upload one above.")
    st.stop()

for iv in interviews:
    with st.container(border=True):
        col_info, col_actions = st.columns([3, 1])

        with col_info:
            st.markdown(f"**{iv['title'] or 'Untitled'}**")
            st.caption(
                f"{iv['interviewee_name'] or 'Unknown'} "
                f"| {iv['interviewee_role'] or 'N/A'} "
                f"| Status: {iv['status']} "
                f"| Source: {iv['source_type']} "
                f"| {iv['created_at'][:10] if iv.get('created_at') else ''}"
            )

        with col_actions:
            # Run extraction analysis button
            if st.button("Run Extraction", key=f"extract_{iv['id']}"):
                with st.spinner("Queueing extraction ..."):
                    try:
                        resp = _api("post", f"/analysis/jobs/extract/{iv['id']}")
                        resp.raise_for_status()
                        job = resp.json()
                        final = _wait_for_job(job["id"])
                        if final.get("status") == "completed":
                            result = final.get("result", {})
                            st.success(
                                f"Extracted: {result.get('jobs_count', 0)} jobs, "
                                f"{result.get('pain_points_count', 0)} pains, "
                                f"{result.get('workarounds_count', 0)} workarounds, "
                                f"{result.get('opportunities_count', 0)} opportunities"
                            )
                        elif final.get("status") == "failed":
                            st.error(f"Extraction failed: {final.get('error_message', 'unknown error')}")
                        else:
                            st.info(f"Extraction job queued: `{job['id']}` (still running)")
                    except httpx.HTTPError as exc:
                        st.error(f"Extraction failed: {exc}")

            # Delete interview button
            if st.button("Delete", key=f"delete_{iv['id']}"):
                try:
                    resp = _api("delete", f"/interviews/detail/{iv['id']}")
                    resp.raise_for_status()
                    st.success("Interview deleted.")
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Delete failed: {exc}")
