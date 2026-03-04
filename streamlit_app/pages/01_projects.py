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

project_options = {p["id"]: f"{p['name']}  ({p['interview_count']} interviews)" for p in projects}

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
