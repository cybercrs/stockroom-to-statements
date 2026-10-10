"""Compact accessible navigation and a widget-free review renderer."""

import streamlit as st
from copy import deepcopy


def arrows(view, reached, total, move):
    st.markdown(
        """
        <style>
        /* Preserve the native sidebar opener used by reset/facilitator controls. */
        [data-testid="stHeader"] { visibility: visible; background: transparent; }
        [data-testid="stToolbar"] { visibility: visible; height: 100%; }
        [data-testid="stHeaderActionElements"] { display: none; }
        .st-key-browser_navigation button {
            width: 44px; height: 44px; min-width: 44px; min-height: 44px;
            position: relative; padding: 0; border: 1px solid #C5CCD8; border-radius: 6px;
            background: transparent; color: #59677A; box-shadow: none;
        }
        .st-key-browser_navigation button::before {
            content: ""; position: absolute; width: 20px; height: 20px;
            top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2359677A' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19 12H5m0 0 7-7m-7 7 7 7'/%3E%3C/svg%3E");
        }
        .st-key-browser_forward button::before { transform: translate(-50%, -50%) rotate(180deg); }
        /* Keep the native labels in the accessibility tree, beside decorative icons. */
        .st-key-browser_navigation button p {
            position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
            overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0;
        }
        .st-key-browser_navigation button:hover:not(:disabled) {
            background: #E6EAF1; color: #14213D; border-color: #A7B2C3;
        }
        .st-key-browser_navigation button:focus-visible {
            outline: 2px solid #003087; outline-offset: 2px;
        }
        .st-key-browser_navigation button:disabled { opacity: 0.55; }
        .st-key-browser_navigation [data-testid="stCaptionContainer"] p {
            color: #59677A; font-size: 0.75rem; margin: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(
        key="browser_navigation",
        horizontal=True,
        horizontal_alignment="right",
        vertical_alignment="center",
        gap="xsmall",
    ):
        st.caption(f"Page {view + 1} of {total}", width="content")
        st.button(
            "Back",
            width=44,
            key="browser_back",
            disabled=view == 0,
            help="Back: review the previous reached page. Earlier pages are read-only.",
            on_click=move,
            args=(-1,),
        )
        st.button(
            "Forward",
            width=44,
            key="browser_forward",
            disabled=view >= reached,
            help="Forward: review the next reached page. Use the current page's validation controls to advance.",
            on_click=move,
            args=(1,),
        )


class FrozenState(dict):
    """A defensive view copy: renderer writes can never affect earned progress."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as error:
            raise AttributeError(key) from error

    def __setattr__(self, key, value):
        self[key] = value


class ReviewUI:
    def __init__(self, state):
        self.session_state = FrozenState(deepcopy(dict(state)))

    def __getattr__(self, name):
        return getattr(st, name)

    def button(self, *args, **kwargs):
        return False

    def radio(self, label, options, **kwargs):
        index = kwargs.get("index", 0)
        value = options[index] if index is not None else None
        if value is not None:
            st.write(f"{label}: {value}")
        return value

    def number_input(self, label, **kwargs):
        value = kwargs.get("value", 0)
        st.write(f"{label}: {value}")
        return value
