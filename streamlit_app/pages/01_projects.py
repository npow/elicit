"""Projects page -- create, list, and select discovery projects."""

import streamlit as st
import httpx

st.set_page_config(page_title="Projects", layout="wide")

API_BASE = st.session_state.get("api_base", "http://localhost:8000/api")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(method: str, path: str, **kwargs) -> httpx.Response:
    """Execute a synchronous HTTP request against the backend."""
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=30.0) as client:
        return getattr(client, method)(url, **kwargs)


def _fetch_projects() -> list[dict]:
    """Return all projects from the API, or an empty list on error."""
    try:
        resp = _api("get", "/projects/")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        st.error(f"Failed to fetch projects: {exc}")
        return []


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Projects")
st.markdown("Create and manage your customer-discovery projects.")
st.divider()

# ---------------------------------------------------------------------------
# Create project form
# ---------------------------------------------------------------------------

with st.expander("Create New Project", expanded=False):
    with st.form("create_project_form"):
        name = st.text_input("Project Name *", placeholder="e.g. B2B Onboarding Discovery")
        description = st.text_area("Description", placeholder="What are you trying to learn?")
        hypothesis = st.text_area(
            "Hypothesis",
            placeholder="e.g. SMB SaaS teams waste >5 hrs/week onboarding new hires manually",
        )
        target_customer = st.text_input(
            "Target Customer",
            placeholder="e.g. Head of People Ops at 50-200 person SaaS companies",
        )
        submitted = st.form_submit_button("Create Project")

    if submitted:
        if not name.strip():
            st.warning("Project name is required.")
        else:
            try:
                resp = _api(
                    "post",
                    "/projects/",
                    json={
                        "name": name.strip(),
                        "description": description.strip(),
                        "hypothesis": hypothesis.strip(),
                        "target_customer": target_customer.strip(),
                    },
                )
                resp.raise_for_status()
                project = resp.json()
                st.success(f"Project **{project['name']}** created!")
                st.session_state["project_id"] = project["id"]
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Failed to create project: {exc}")

# ---------------------------------------------------------------------------
# List & select projects
# ---------------------------------------------------------------------------

projects = _fetch_projects()

if not projects:
    st.info("No projects yet. Create one above to get started.")
    st.stop()

project_options = {p.get("id", ""): f"{p.get('name', 'Unnamed')}  ({p.get('interview_count', 0)} interviews)" for p in projects if p.get("id")}

# Pre-select the stored project, if any
current_project_id = st.session_state.get("project_id")
default_index = 0
if current_project_id and current_project_id in project_options:
    default_index = list(project_options.keys()).index(current_project_id)

selected_id = st.selectbox(
    "Select a Project",
    options=list(project_options.keys()),
    format_func=lambda pid: project_options[pid],
    index=default_index,
    key="project_selector",
)

if selected_id:
    st.session_state["project_id"] = selected_id

# ---------------------------------------------------------------------------
# Show project details
# ---------------------------------------------------------------------------

selected_project = next((p for p in projects if p["id"] == selected_id), None)

if selected_project:
    st.divider()
    st.subheader(selected_project["name"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Interviews", selected_project["interview_count"])
    col2.metric("Created", selected_project["created_at"][:10] if selected_project["created_at"] else "N/A")
    col3.metric("Target Customer", selected_project["target_customer"] or "Not set")

    st.markdown("**Description**")
    st.write(selected_project["description"] or "_No description provided._")

    st.markdown("**Hypothesis**")
    st.write(selected_project["hypothesis"] or "_No hypothesis set._")

    # ---------------------------------------------------------------------------
    # Discovery progress status
    # ---------------------------------------------------------------------------
    st.divider()
    st.markdown("**Discovery Progress**")

    try:
        ivs_resp = _api("get", f"/interviews/{selected_id}")
        ivs_resp.raise_for_status()
        all_ivs = ivs_resp.json()
        analyzed = [iv for iv in all_ivs if iv.get("status") == "analyzed"]
        n_total = len(all_ivs)
        n_analyzed = len(analyzed)
    except httpx.HTTPError:
        all_ivs, n_total, n_analyzed = [], 0, 0

    try:
        pat_resp = _api("get", f"/analysis/patterns/{selected_id}")
        pat_resp.raise_for_status()
        n_patterns = len(pat_resp.json())
    except httpx.HTTPError:
        n_patterns = 0

    try:
        rec_resp = _api("get", f"/analysis/recommendations/{selected_id}")
        rec_resp.raise_for_status()
        n_recs = len(rec_resp.json())
    except httpx.HTTPError:
        n_recs = 0

    steps = [
        ("1. Upload interviews", n_total > 0, f"{n_total} uploaded"),
        ("2. Extract insights", n_analyzed > 0, f"{n_analyzed}/{n_total} analyzed"),
        ("3. Synthesize patterns", n_patterns > 0, f"{n_patterns} patterns found"),
        ("4. Generate recommendations", n_recs > 0, f"{n_recs} recommendations"),
    ]

    for label, done, detail in steps:
        icon = "✅" if done else "⬜"
        st.markdown(f"{icon} **{label}** — {detail}")

    # ---- Delete project ----
    st.divider()
    with st.expander("Danger Zone"):
        if st.button("Delete This Project", type="primary"):
            try:
                resp = _api("delete", f"/projects/{selected_id}")
                resp.raise_for_status()
                st.success("Project deleted.")
                if st.session_state.get("project_id") == selected_id:
                    del st.session_state["project_id"]
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Delete failed: {exc}")
