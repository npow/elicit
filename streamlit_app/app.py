"""Main Streamlit app entry point with sidebar navigation."""

import streamlit as st

st.set_page_config(
    page_title="Elicit",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000/api"

# Store API base in session state for pages to use
if "api_base" not in st.session_state:
    st.session_state.api_base = API_BASE

st.sidebar.title("Elicit")
st.sidebar.caption("Elicit what matters from customer interviews.")
st.sidebar.divider()

st.title("Welcome to Elicit")
st.markdown("""
### Elicit what matters from customer interviews. Build the right thing.

Navigate using the sidebar pages to:

1. **Projects** — Create and manage discovery projects
2. **Upload** — Add interview transcripts (text or audio)
3. **Analysis** — View extracted JTBD, pains, and workarounds
4. **Opportunity Tree** — Visualize your Opportunity Solution Tree
5. **Recommendations** — See prioritized "build this next" insights
6. **Interview Prep** — Generate Mom Test interview guides
7. **Interview Review** — Score your interview quality
8. **Simulator** — Practice with synthetic interviewees
9. **Calibration** — Track synthetic vs real accuracy

---

**Getting started:** Create a project, upload a transcript, and run analysis.
""")
