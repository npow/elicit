"""Simulator page -- synthetic interview practice with AI personas."""

import streamlit as st
import httpx

st.set_page_config(page_title="Interview Simulator", layout="wide")

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
# Session-state initialization for chat
# ---------------------------------------------------------------------------

if "sim_session_id" not in st.session_state:
    st.session_state.sim_session_id = None
if "sim_messages" not in st.session_state:
    st.session_state.sim_messages = []
if "sim_persona_name" not in st.session_state:
    st.session_state.sim_persona_name = ""

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Interview Simulator")
st.markdown("Practice your interviewing skills with **AI-generated synthetic personas**.")
project_id = _require_project()
st.caption(f"Project ID: `{project_id}`")
st.divider()

# ---------------------------------------------------------------------------
# Generate personas
# ---------------------------------------------------------------------------

st.subheader("Generate Personas")

gen_cols = st.columns([2, 2, 1])
with gen_cols[0]:
    persona_count = st.number_input("How many personas?", min_value=1, max_value=10, value=3)
with gen_cols[1]:
    adversarial = st.checkbox("Include adversarial personas", value=False)
with gen_cols[2]:
    st.write("")  # spacer
    st.write("")
    generate_btn = st.button("Generate")

if generate_btn:
    with st.spinner("Generating personas ..."):
        try:
            resp = _api(
                "post",
                f"/simulation/personas/{project_id}",
                json={"count": persona_count, "is_adversarial": adversarial},
            )
            resp.raise_for_status()
            personas = resp.json()
            st.success(f"Generated {len(personas)} persona(s).")
            st.rerun()
        except httpx.HTTPError as exc:
            st.error(f"Persona generation failed: {exc}")

# ---------------------------------------------------------------------------
# List personas
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Available Personas")

try:
    resp = _api("get", f"/simulation/personas/{project_id}")
    resp.raise_for_status()
    personas = resp.json()
except httpx.HTTPError as exc:
    st.error(f"Failed to load personas: {exc}")
    personas = []

if not personas:
    st.info("No personas yet. Generate some above.")
    st.stop()

# Show personas in a grid
persona_cols = st.columns(min(len(personas), 3))
for idx, persona in enumerate(personas):
    col = persona_cols[idx % 3]
    with col:
        with st.container(border=True):
            st.markdown(f"**{persona['name']}**")
            st.caption(f"{persona['role']} at {persona.get('company_type', 'Unknown')}")
            if persona.get("is_adversarial"):
                st.markdown(":red[Adversarial]")
            if persona.get("background"):
                st.write(persona["background"][:200] + ("..." if len(persona.get("background", "")) > 200 else ""))

            # Show details in expander
            with st.expander("Details"):
                if persona.get("goals"):
                    st.markdown("**Goals:**")
                    for g in persona["goals"]:
                        st.markdown(f"- {g}")
                if persona.get("frustrations"):
                    st.markdown("**Frustrations:**")
                    for f in persona["frustrations"]:
                        st.markdown(f"- {f}")
                if persona.get("current_tools"):
                    st.markdown("**Current Tools:**")
                    for t in persona["current_tools"]:
                        st.markdown(f"- {t}")
                if persona.get("behavioral_traits"):
                    st.markdown("**Behavioral Traits:**")
                    for bt in persona["behavioral_traits"]:
                        st.markdown(f"- {bt}")

            # Start interview button
            if st.button("Start Interview", key=f"start_{persona['id']}"):
                with st.spinner("Starting interview session ..."):
                    try:
                        resp = _api("post", f"/simulation/sessions/{persona['id']}/start")
                        resp.raise_for_status()
                        session = resp.json()
                        st.session_state.sim_session_id = session["id"]
                        st.session_state.sim_persona_name = persona["name"]
                        # Initialize messages from session (may have welcome message)
                        st.session_state.sim_messages = session.get("messages") or []
                        st.rerun()
                    except httpx.HTTPError as exc:
                        st.error(f"Failed to start session: {exc}")

# ---------------------------------------------------------------------------
# Active chat interface
# ---------------------------------------------------------------------------

if st.session_state.sim_session_id:
    st.divider()
    st.subheader(f"Interview with {st.session_state.sim_persona_name}")

    # End session button
    end_col, _, status_col = st.columns([1, 3, 1])
    with end_col:
        if st.button("End Interview", type="primary"):
            with st.spinner("Ending session ..."):
                try:
                    resp = _api("post", f"/simulation/sessions/{st.session_state.sim_session_id}/end")
                    resp.raise_for_status()
                    final_session = resp.json()
                    st.session_state.sim_session_id = None
                    st.session_state.sim_messages = []
                    st.session_state.sim_persona_name = ""

                    # Show final quality score if available
                    quality = final_session.get("session_quality_score")
                    if quality is not None:
                        st.info(f"Session quality score: **{int(quality * 100)}%**")

                    st.success("Interview session ended.")
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Failed to end session: {exc}")

    with status_col:
        st.caption(f"Session: `{st.session_state.sim_session_id[:8]}...`")

    # Display message history
    for msg in st.session_state.sim_messages:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        with st.chat_message(role):
            st.write(content)

            # Show mom-test feedback if present
            if msg.get("mom_test_feedback"):
                feedback = msg["mom_test_feedback"]
                if isinstance(feedback, dict):
                    is_valid = feedback.get("is_valid", True)
                    if not is_valid:
                        st.warning(f"Mom Test Violation: {feedback.get('reason', 'Leading question detected')}")
                    if feedback.get("suggestion"):
                        st.caption(f"Suggestion: {feedback['suggestion']}")
                elif isinstance(feedback, str):
                    st.caption(f"Feedback: {feedback}")

    # Chat input
    user_input = st.chat_input("Type your interview question ...")
    if user_input:
        # Add user message to display
        st.session_state.sim_messages.append({"role": "user", "content": user_input})

        # Send to backend
        try:
            resp = _api(
                "post",
                f"/simulation/sessions/{st.session_state.sim_session_id}/message",
                json={"role": "user", "content": user_input},
            )
            resp.raise_for_status()
            result = resp.json()

            # The response may contain the persona reply and optional mom-test feedback
            persona_reply = (
                result.get("response")
                or result.get("reply")
                or result.get("content")
                or result.get("message", "")
            )
            mom_test_feedback = result.get("mom_test_validation") or result.get("mom_test_feedback")

            reply_msg = {"role": "assistant", "content": persona_reply}
            if mom_test_feedback:
                reply_msg["mom_test_feedback"] = mom_test_feedback

            st.session_state.sim_messages.append(reply_msg)
            st.rerun()
        except httpx.HTTPError as exc:
            st.error(f"Message failed: {exc}")
