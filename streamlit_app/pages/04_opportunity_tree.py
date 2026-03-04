"""Opportunity Tree page -- visualize the Opportunity Solution Tree."""

import streamlit as st
import httpx

st.set_page_config(page_title="Opportunity Tree", layout="wide")

API_BASE = st.session_state.get("api_base", "http://localhost:8000/api")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=30.0) as client:
        return getattr(client, method)(url, **kwargs)


def _require_project() -> str:
    pid = st.session_state.get("project_id")
    if not pid:
        st.warning("Please select a project on the **Projects** page first.")
        st.stop()
    return pid


# Color mappings by node type
TYPE_COLORS = {
    "job": "#1E88E5",       # blue
    "pain": "#E53935",      # red
    "pain_point": "#E53935",
    "opportunity": "#43A047",  # green
    "workaround": "#FB8C00",  # orange
    "outcome": "#8E24AA",     # purple
}

TYPE_ICONS = {
    "job": "briefcase",
    "pain": "warning",
    "pain_point": "warning",
    "opportunity": "lightbulb",
    "workaround": "wrench",
    "outcome": "star",
}


def _render_tree_node(node: dict, depth: int = 0) -> None:
    """Recursively render a tree node with nested expanders."""
    node_type = node.get("type", "unknown").lower()
    color = TYPE_COLORS.get(node_type, "#757575")
    label = (
        node.get("name")
        or node.get("label")
        or node.get("description")
        or node.get("statement")
        or "Unnamed"
    )
    score = node.get("score") or node.get("opportunity_score")

    score_str = f" (score: {score:.2f})" if score is not None else ""

    indent = "&nbsp;" * (depth * 4)

    # Use expander for nodes with children; plain container otherwise
    children = node.get("children", [])
    if children:
        with st.expander(f"{indent}{label}{score_str}", expanded=(depth < 2)):
            st.markdown(
                f"<span style='color:{color}; font-weight:bold;'>{node_type.upper()}</span>",
                unsafe_allow_html=True,
            )
            if node.get("supporting_quote"):
                st.markdown(f"> *\"{node['supporting_quote']}\"*")
            if node.get("confidence") is not None:
                st.progress(float(node["confidence"]), text=f"Confidence: {int(float(node['confidence']) * 100)}%")
            for child in children:
                _render_tree_node(child, depth + 1)
    else:
        with st.container(border=True):
            st.markdown(
                f"{indent}<span style='color:{color}; font-weight:bold;'>{node_type.upper()}</span>"
                f" &mdash; {label}{score_str}",
                unsafe_allow_html=True,
            )
            if node.get("supporting_quote"):
                st.markdown(f"> *\"{node['supporting_quote']}\"*")
            if node.get("confidence") is not None:
                st.progress(float(node["confidence"]), text=f"Confidence: {int(float(node['confidence']) * 100)}%")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Opportunity Solution Tree")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Fetch the tree
# ---------------------------------------------------------------------------

try:
    resp = _api("get", f"/analysis/opportunity-tree/{project_id}")
    resp.raise_for_status()
    tree_data = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load opportunity tree: {exc}")
    tree_data = None

if not tree_data:
    st.info(
        "No opportunity tree data yet. Run extraction and synthesis from the **Analysis** page first."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Render the tree
# ---------------------------------------------------------------------------

st.subheader("Tree View")

# The tree may be a single root node or a list of root nodes
if isinstance(tree_data, list):
    for root_node in tree_data:
        _render_tree_node(root_node, depth=0)
elif isinstance(tree_data, dict):
    # Could be {"root": {...}} or a direct node dict
    root = tree_data.get("root") or tree_data.get("tree") or tree_data
    if isinstance(root, list):
        for node in root:
            _render_tree_node(node, depth=0)
    else:
        _render_tree_node(root, depth=0)
else:
    st.warning("Unexpected tree format.")
    st.json(tree_data)

# ---------------------------------------------------------------------------
# Top opportunities
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Top Opportunities")

try:
    resp = _api("get", f"/analysis/top-opportunities/{project_id}", params={"limit": 10})
    resp.raise_for_status()
    top_opps = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load top opportunities: {exc}")
    top_opps = []

if not top_opps:
    st.info("No ranked opportunities available yet.")
else:
    for rank, opp in enumerate(top_opps, start=1):
        with st.container(border=True):
            cols = st.columns([1, 4, 2])
            with cols[0]:
                st.markdown(f"### #{rank}")
            with cols[1]:
                desc = opp.get("description") or opp.get("label") or "Unnamed opportunity"
                st.markdown(f"**{desc}**")
                if opp.get("market_size_indicator"):
                    st.caption(f"Market size: {opp['market_size_indicator']}")
            with cols[2]:
                score = opp.get("opportunity_score", 0)
                st.metric("Opportunity Score", f"{score:.2f}")

# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Legend")
legend_cols = st.columns(len(TYPE_COLORS))
for col, (node_type, color) in zip(legend_cols, TYPE_COLORS.items()):
    col.markdown(
        f"<span style='color:{color}; font-size:1.1em; font-weight:bold;'>"
        f"&#9679; {node_type.replace('_', ' ').title()}</span>",
        unsafe_allow_html=True,
    )
