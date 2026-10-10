"""Browser driver using original teaching renderers and validated progress."""

from pathlib import Path
import runpy
import streamlit as st
from browser.navigation import (
    VIEW_KEY,
    VIEW_PARAM,
    STAGE_KEY,
    SCROLL_KEY,
    POSITIONS,
    RENDERERS,
    frontier,
    restore_view,
    move,
    advance,
)
from browser.ui import arrows, ReviewUI
from stockroom_to_statements.progress import reset_saved_progress, sync_progress_query

app = runpy.run_path(
    str(Path(__file__).with_name("shared_app.py")), run_name="browser_renderer"
)
globals_ = app["set_stage"].__globals__


def restart():
    if st.session_state[VIEW_KEY] < frontier(st.session_state):
        return
    reset_saved_progress(st.session_state, st.query_params)
    st.session_state[VIEW_KEY] = 0
    st.session_state[SCROLL_KEY] = True


def advance_current(*args):
    advance(st.session_state)


def navigate(direction):
    move(st.session_state, direction)


globals_.update(
    set_stage=advance_current, advance_item=advance_current, restart_activity=restart
)
app["initialize_state"]()
if VIEW_KEY not in st.session_state:
    restore_view(st.session_state, st.query_params.get(VIEW_PARAM))
view = st.session_state[VIEW_KEY]
reached = frontier(st.session_state)
reviewing = view < reached
st.markdown(app["APP_CSS"], unsafe_allow_html=True)
app["render_hero"]()
arrows(view, reached, len(POSITIONS), navigate)
with st.sidebar:
    st.header("Stockroom to Statements")
    st.write(
        "Progress is saved anonymously in this page's address. Refresh or bookmark to resume."
    )
    st.button("Start over", on_click=restart, disabled=reviewing)
if reviewing:
    st.info("Review only. Return to your current page to continue the activity.")
    ui = ReviewUI(st.session_state)
    stage, key, index = POSITIONS[view]
    ui.session_state[STAGE_KEY] = stage
    if key:
        ui.session_state[key] = index
    globals_["st"] = ui
else:
    stage = st.session_state[STAGE_KEY]
app["render_stage_row"]()
app[RENDERERS[stage]]()
sync_progress_query(st.session_state, st.query_params)
if st.query_params.get(VIEW_PARAM) != str(st.session_state[VIEW_KEY]):
    st.query_params[VIEW_PARAM] = str(st.session_state[VIEW_KEY])
globals_["st"] = st
app["render_scroll_reset"]()
