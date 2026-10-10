"""Student-facing Streamlit application for Stockroom to Statements."""

from __future__ import annotations

import hashlib

import random

from html import escape

import streamlit as st

from stockroom_to_statements.case_data import (
    ANALYSIS_FIELDS,
    ANALYSIS_INTERPRETATION_OPTIONS,
    ANALYSIS_RECOMMENDATION_OPTIONS,
    BEGINNING_UNIT_COST,
    BEGINNING_UNITS,
    COMPANY_NAME,
    COST_FIELDS,
    COUNT_DECISIONS,
    DAYS_BENCHMARK,
    INBOUND_SHIPPING_POINT_UNITS,
    PHYSICAL_COUNT,
    PURCHASE_UNIT_COST,
    PURCHASE_UNITS,
    QUANTITY_EFFECT_OPTIONS,
    QUANTITY_FIELDS,
    REPORTING_DATE,
    REPORTING_DECISIONS,
    SALES_REVENUE,
    CONSIGNED_UNITS,
    OUTBOUND_DESTINATION_UNITS,
    TURNOVER_BENCHMARK,
)

from stockroom_to_statements.engine import (
    evaluate_analysis,
    evaluate_costing,
    evaluate_decision,
    evaluate_quantity,
    format_currency,
    inventory_metrics,
    method_results,
)

from stockroom_to_statements.progress import (
    SNAPSHOT_PARAM,
    activity_defaults,
    record_attempt,
    reset_saved_progress,
    restore_session_state,
    score_summary,
    sync_progress_query,
)

st.set_page_config(
    page_title="Stockroom to Statements",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="collapsed",
)

UD_RED = "#CE0037"

UD_BLUE = "#003087"

INK = "#14213D"

MUTED = "#59677A"

BACKGROUND = "#F4F7FB"

SUCCESS = "#137A4B"

WARNING = "#986000"

GOLD = "#F3B61F"

APP_CSS = f"""
<style>
    :root {{
        --ud-red: {UD_RED};
        --ud-blue: {UD_BLUE};
        --ink: {INK};
        --muted: {MUTED};
        --background: {BACKGROUND};
        --success: {SUCCESS};
        --warning: {WARNING};
        --gold: {GOLD};
    }}

    .stApp {{ background: var(--background); }}
    section[data-testid="stMain"] {{ overflow-anchor: none; }}
    [data-testid="stHeaderActionElements"] {{ display: none; }}
    [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}
    [data-testid="stDecoration"] {{ background: var(--ud-red); }}
    [data-testid="stIFrame"], iframe[title="st.iframe"] {{ height: 0 !important; min-height: 0 !important; border: 0 !important; }}
    div[data-testid="stElementContainer"]:has(iframe[title="st.iframe"]) {{ height: 0 !important; min-height: 0 !important; margin: 0 !important; }}
    .block-container {{ max-width: 1160px; padding-top: 1.35rem; padding-bottom: 4rem; }}
    h1, h2, h3 {{ color: var(--ink); letter-spacing: -0.02em; }}
    p, li, label {{ color: var(--ink); }}

    .hero {{
        background:
            radial-gradient(circle at 92% 10%, rgba(243, 182, 31, 0.32), transparent 25%),
            linear-gradient(125deg, #001F55 0%, var(--ud-blue) 60%, #164E91 100%);
        border-top: 7px solid var(--ud-red);
        border-radius: 18px;
        box-shadow: 0 16px 38px rgba(0, 48, 135, 0.17);
        margin-bottom: 1rem;
        padding: 2rem 2.2rem 1.8rem;
    }}
    .hero-kicker {{ color: #FFFFFF; font-size: 0.8rem; font-weight: 850; letter-spacing: 0.13em; }}
    .hero h1 {{ color: #FFFFFF; font-size: clamp(2.15rem, 5vw, 3.7rem); margin: 0.15rem 0 0; }}
    .hero p {{ color: #F1F5FF; font-size: 1.08rem; margin: 0.65rem 0 0; max-width: 850px; }}
    .hero strong {{ color: var(--gold); }}

    .stage-row {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.38rem; margin: 0 0 1.3rem; }}
    .stage-pill {{
        background: #E6EAF1; border: 1px solid #D3D9E4; border-radius: 999px;
        color: #5C6879; font-size: 0.71rem; font-weight: 760; padding: 0.46rem 0.42rem; text-align: center;
    }}
    .stage-pill.complete {{ background: #E5F3EB; border-color: #A5D2B9; color: #0A653D; }}
    .stage-pill.active {{ background: var(--ud-red); border-color: var(--ud-red); color: #FFFFFF; }}

    .eyebrow {{ color: var(--ud-red); font-size: 0.78rem; font-weight: 850; letter-spacing: 0.1em; text-transform: uppercase; }}
    .lead {{ color: var(--muted); font-size: 1.07rem; max-width: 900px; }}
    .card {{
        background: #FFFFFF; border: 1px solid #D9E0EA; border-left: 7px solid var(--ud-blue);
        border-radius: 14px; box-shadow: 0 8px 22px rgba(20, 33, 61, 0.06);
        margin: 0.75rem 0 1rem; padding: 1.15rem 1.3rem;
    }}
    .card .document {{ color: var(--ud-blue); font-size: 0.78rem; font-weight: 850; letter-spacing: 0.06em; text-transform: uppercase; }}
    .card h3 {{ margin: 0.28rem 0 0.48rem; }}
    .card p {{ font-size: 1.04rem; margin: 0; }}

    .concept-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.72rem; margin: 1rem 0 1.3rem; }}
    .concept-card {{ background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 13px; padding: 1rem; }}
    .concept-card strong {{ color: var(--ud-blue); display: block; margin: 0.2rem 0; }}
    .concept-number {{ color: var(--ud-red); font-size: 1.15rem; font-weight: 900; }}
    .concept-card span {{ color: var(--muted); font-size: 0.9rem; }}

    .layer-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.8rem; margin: 0.85rem 0 1rem; }}
    .layer-card {{ background: #FFFFFF; border: 1px solid #CBD5E2; border-radius: 13px; overflow: hidden; }}
    .layer-label {{ background: var(--ud-blue); color: #FFFFFF; font-size: 0.8rem; font-weight: 850; padding: 0.55rem 0.8rem; }}
    .layer-body {{ padding: 0.9rem; }}
    .layer-body strong {{ color: var(--ink); display: block; font-size: 1.35rem; }}
    .layer-body span {{ color: var(--muted); }}

    .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.65rem; margin: 0.9rem 0 1.1rem; }}
    .analysis-metric-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.65rem; margin: 0.9rem 0 1.1rem; }}
    .metric-box {{ background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 12px; padding: 0.85rem; text-align: center; }}
    .metric-box strong {{ color: var(--ud-blue); display: block; font-size: 1.35rem; }}
    .metric-box span {{ color: var(--muted); font-size: 0.8rem; }}

    .feedback-row {{
        align-items: flex-start; background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 10px;
        display: flex; gap: 1rem; justify-content: space-between; margin: 0.42rem 0; padding: 0.7rem 0.82rem;
    }}
    .feedback-row.correct {{ border-left: 5px solid var(--success); }}
    .feedback-row.review {{ border-left: 5px solid var(--warning); }}
    .feedback-label {{ font-weight: 780; }}
    .feedback-detail {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.12rem; }}
    .feedback-value {{ font-variant-numeric: tabular-nums; text-align: right; }}

    .effect-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.65rem; margin: 0.7rem 0; }}
    .effect-box {{ background: #EEF4FF; border: 1px solid #C6D7F2; border-radius: 11px; padding: 0.82rem 0.95rem; }}
    .effect-box span {{ color: var(--muted); display: block; font-size: 0.76rem; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase; }}
    .effect-box strong {{ color: var(--ud-blue); display: block; font-size: 0.95rem; margin-top: 0.25rem; }}

    .method-table {{ border-collapse: collapse; margin: 0.8rem 0 1rem; width: 100%; }}
    .method-table th {{ background: var(--ud-blue); color: #FFFFFF; padding: 0.72rem; text-align: right; }}
    .method-table th:first-child {{ text-align: left; }}
    .method-table td {{ background: #FFFFFF; border-bottom: 1px solid #D9E0EA; padding: 0.72rem; text-align: right; }}
    .method-table td:first-child {{ color: var(--ud-blue); font-weight: 800; text-align: left; }}

    .chain {{ align-items: stretch; display: grid; gap: 0.45rem; grid-template-columns: repeat(5, 1fr); margin: 1rem 0; }}
    .chain-step {{ background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 10px; color: var(--ud-blue); font-weight: 800; padding: 0.78rem; text-align: center; }}

    .stButton > button, .stFormSubmitButton > button {{ border-radius: 9px; font-weight: 760; min-height: 2.7rem; }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: var(--ud-red); border-color: var(--ud-red); color: #FFFFFF; }}
    button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {{ background: var(--ud-red); border-color: var(--ud-red); color: #FFFFFF; }}
    button[data-testid="stBaseButton-primary"] p, button[data-testid="stBaseButton-primaryFormSubmit"] p {{ color: #FFFFFF !important; }}

    @media (max-width: 820px) {{
        .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
        .hero {{ padding: 1.4rem 1.2rem; }}
        .stage-row {{ grid-template-columns: 1fr; }}
        .stage-pill {{ display: none; }}
        .stage-pill.active {{ display: block; }}
        .concept-grid, .layer-grid, .metric-grid, .analysis-metric-grid, .effect-grid, .chain {{ grid-template-columns: 1fr; }}
        .feedback-row {{ display: block; }}
        .feedback-value {{ margin-top: 0.3rem; text-align: left; }}
        .method-table {{ font-size: 0.82rem; }}
    }}
</style>
"""

STAGE_LABELS = ("Brief", "1. Screen", "2. Quantity", "3. Cost", "4. Effects", "5. Analyze", "Complete")

QUANTITY_HINTS = {
    "ending_units": "Begin with the warehouse count, remove goods owned by others, and add the in-transit shipments still owned by Flyer Cycle Works.",
    "shrinkage_units": "Compare the accounting system's 44 units with your corrected ending inventory quantity.",
}

COST_HINTS = {
    "fifo_ending_inventory": "Under FIFO, identify which layer's unit cost remains in the 40 ending units.",
    "fifo_cogs": "After determining FIFO ending Inventory, assign the rest of total cost available to sold units.",
    "lifo_ending_inventory": "Under LIFO, identify which layer's unit cost remains in the 40 ending units.",
    "lifo_cogs": "After determining LIFO ending Inventory, assign the rest of total cost available to sold units.",
    "average_unit_cost": "Blend both layers by dividing their combined cost by their combined units.",
    "average_ending_inventory": "Apply your weighted-average unit cost to the 40 ending units.",
    "average_cogs": "Assign the portion of total cost available that does not remain in average-cost ending Inventory to sold units.",
}

ANALYSIS_HINTS = {
    "average_inventory": "Average the beginning Inventory balance and FIFO ending Inventory balance.",
    "inventory_turnover": "Compare FIFO Cost of Goods Sold with the average Inventory balance you calculated.",
    "days_in_inventory": "Convert turnover into days using a 365-day year.",
}

def initialize_state() -> None:
    if "sts_restore_attempted" not in st.session_state:
        restored = restore_session_state(st.session_state, st.query_params.get(SNAPSHOT_PARAM))
        st.session_state.sts_restore_attempted = True
        if restored:
            st.session_state.sts_scroll_to_top = True
    for key, value in activity_defaults().items():
        if key not in st.session_state:
            st.session_state[key] = value

def restart_activity() -> None:
    reset_saved_progress(st.session_state, st.query_params)
    st.session_state.sts_scroll_to_top = True

def set_stage(stage: int) -> None:
    st.session_state.sts_stage = stage
    st.session_state.sts_scroll_to_top = True

def advance_item(index_key: str, count: int, next_stage: int) -> None:
    index = int(st.session_state[index_key])
    if index >= count - 1:
        set_stage(next_stage)
    else:
        st.session_state[index_key] = index + 1
        st.session_state.sts_scroll_to_top = True

def selected_index(options: tuple | list, selected: str | None) -> int | None:
    return list(options).index(selected) if selected in options else None

def shuffled(items: tuple | list, salt: str) -> list:
    """Return a stable learner-specific order that survives reruns and refreshes."""

    digest = hashlib.sha256(f"{st.session_state.sts_shuffle_seed}:{salt}".encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    ordered = list(items)
    rng.shuffle(ordered)
    if len(ordered) > 1 and ordered == list(items):
        ordered = ordered[1:] + ordered[:1]
    return ordered

def escape_dollar_markdown(value: object) -> str:
    """Keep dollar signs in learner-facing text from starting inline math."""

    return str(value).replace("$", r"\$")

def save_draft(group: str, answer_key: str, widget_key: str) -> None:
    """Persist unfinished work outside widget state so a refresh can restore it."""

    drafts = {key: dict(value) for key, value in st.session_state.sts_drafts.items()}
    group_answers = dict(drafts[group])
    value = st.session_state.get(widget_key)
    if value is None:
        group_answers.pop(answer_key, None)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        group_answers[answer_key] = value
    else:
        group_answers[answer_key] = str(value)
    drafts[group] = group_answers
    st.session_state.sts_drafts = drafts

def replace_draft(group: str, answers: dict[str, object]) -> None:
    drafts = {key: dict(value) for key, value in st.session_state.sts_drafts.items()}
    drafts[group] = dict(answers)
    st.session_state.sts_drafts = drafts

def render_scroll_reset() -> None:
    """Reset after navigation without overriding learner-initiated scrolling."""

    if not st.session_state.pop("sts_scroll_to_top", False):
        return
    st.iframe(
        """
        <script>
        (() => {
          const parent = window.parent;
          const main = parent.document.querySelector('section[data-testid="stMain"]');
          if (!main) return;
          let cancelled = false;
          let finished = false;
          const scrollingKeys = new Set(['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' ']);
          const cancel = () => { cancelled = true; cleanup(); };
          const cancelKey = (event) => { if (scrollingKeys.has(event.key)) cancel(); };
          const cleanup = () => {
            parent.removeEventListener('wheel', cancel);
            parent.removeEventListener('touchstart', cancel);
            parent.removeEventListener('keydown', cancelKey);
          };
          const reset = () => {
            if (finished) return;
            finished = true;
            if (!cancelled) main.scrollTo({ top: 0, left: 0, behavior: 'auto' });
            cleanup();
          };
          parent.addEventListener('wheel', cancel, { passive: true });
          parent.addEventListener('touchstart', cancel, { passive: true });
          parent.addEventListener('keydown', cancelKey);
          parent.requestAnimationFrame(() => parent.requestAnimationFrame(reset));
          parent.setTimeout(reset, 120);
        })();
        </script>
        """,
        height=1,
        tab_index=-1,
    )

def store_simple_answer(map_key: str, item_id: str, selected: str, score_key: str, correct: bool) -> None:
    responses = dict(st.session_state[map_key])
    responses[item_id] = selected
    st.session_state[map_key] = responses
    record_attempt(st.session_state, score_key, correct)

def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="hero-kicker">YEAR-END INVENTORY CASE</div>
          <h1>Stockroom to Statements</h1>
          <p><strong>What inventory do we own, what is it worth, and what does that information tell us?</strong> Follow one year-end count from physical evidence to account balances, financial statements, and management analysis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_stage_row() -> None:
    current = int(st.session_state.sts_stage)
    pills = []
    for index, label in enumerate(STAGE_LABELS):
        status = "complete" if index < current else "active" if index == current else ""
        pills.append(f'<div class="stage-pill {status}">{escape(label)}</div>')
    st.markdown(f'<div class="stage-row">{"".join(pills)}</div>', unsafe_allow_html=True)

def render_card(document: str, title: str, story: str) -> None:
    st.markdown(
        f"""
        <div class="card">
          <div class="document">{escape(document)}</div>
          <h3>{escape(title)}</h3>
          <p>{escape(story)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_feedback_row(label: str, correct: bool, detail: str, value: str = "") -> None:
    status = "correct" if correct else "review"
    symbol = "Correct" if correct else "Review"
    st.markdown(
        f"""
        <div class="feedback-row {status}">
          <div><div class="feedback-label">{escape(label)} - {symbol}</div><div class="feedback-detail">{escape(detail)}</div></div>
          <div class="feedback-value">{escape(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_effects(account_effect: str, statement_effect: str) -> None:
    st.markdown(
        f"""
        <div class="effect-grid">
          <div class="effect-box"><span>Account change</span><strong>{escape(account_effect)}</strong></div>
          <div class="effect-box"><span>Financial statement effect</span><strong>{escape(statement_effect)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_layers() -> None:
    st.markdown(
        f"""
        <div class="layer-grid">
          <div class="layer-card"><div class="layer-label">Beginning inventory</div><div class="layer-body"><strong>{BEGINNING_UNITS} bicycles at {format_currency(BEGINNING_UNIT_COST)}</strong><span>{format_currency(BEGINNING_UNITS * BEGINNING_UNIT_COST)} total cost</span></div></div>
          <div class="layer-card"><div class="layer-label">One purchase layer</div><div class="layer-body"><strong>{PURCHASE_UNITS} bicycles at {format_currency(PURCHASE_UNIT_COST)}</strong><span>{format_currency(PURCHASE_UNITS * PURCHASE_UNIT_COST)} total cost</span></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_briefing() -> None:
    st.markdown('<div class="eyebrow">Year-end inventory team</div>', unsafe_allow_html=True)
    st.header("One count must support every number that follows")
    st.markdown(
        f'<p class="lead">You are reviewing {escape(COMPANY_NAME)} at {escape(REPORTING_DATE)}. The store has physical goods, customer property, consigned bicycles, and shipments in transit. Management needs an accurate inventory quantity and a clear explanation of how that quantity reaches the financial statements.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="concept-grid">
          <div class="concept-card"><div class="concept-number">01</div><strong>Screen the goods</strong><span>Separate merchandise from property the company does not own or hold for sale.</span></div>
          <div class="concept-card"><div class="concept-number">02</div><strong>Reconcile quantity</strong><span>Adjust the physical count and identify inventory shrinkage.</span></div>
          <div class="concept-card"><div class="concept-number">03</div><strong>Assign cost</strong><span>Use FIFO, LIFO, and weighted average with two cost layers.</span></div>
          <div class="concept-card"><div class="concept-number">04</div><strong>Explain and analyze</strong><span>Determine ending balances, statement effects, turnover, and days in inventory.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Begin the inventory review", type="primary", width="stretch", on_click=set_stage, args=(1,))

def render_sequential_stage(
    *,
    eyebrow: str,
    header: str,
    introduction: str,
    items,
    index_key: str,
    responses_key: str,
    score_prefix: str,
    next_stage: int,
    submit_label: str,
) -> None:
    index = int(st.session_state[index_key])
    item = items[index]
    st.markdown(f'<div class="eyebrow">{escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.header(header)
    st.write(introduction)
    st.progress((index + 1) / len(items), text=f"Decision {index + 1} of {len(items)}")
    render_card(item.evidence, item.title, item.story)

    response = st.session_state[responses_key].get(item.id)
    result = evaluate_decision(item.id, response) if response is not None else None
    if result is not None:
        if result["correct"]:
            st.success(escape_dollar_markdown(f"Correct. {result['explanation']}"))
            render_effects(str(result["account_effect"]), str(result["statement_effect"]))
        else:
            st.warning("That response needs another look.")
            st.info(escape_dollar_markdown(f"Hint: {item.hint}"))
        if result["correct"]:
            st.button(
                "Continue",
                type="primary",
                width="stretch",
                on_click=advance_item,
                args=(index_key, len(items), next_stage),
            )
            return
        st.info("Change your choice below, then check the revised response.")

    draft_group = "count" if score_prefix == "count" else "reporting"
    draft = st.session_state.sts_drafts[draft_group].get(item.id)
    options = shuffled(item.options, f"{score_prefix}-options:{item.id}")
    widget_key = f"widget_{score_prefix}_{item.id}"
    selected = st.radio(
        item.prompt,
        options,
        index=selected_index(options, draft),
        key=widget_key,
        on_change=save_draft,
        args=(draft_group, item.id, widget_key),
        format_func=escape_dollar_markdown,
    )
    button_label = "Check revised response" if response is not None else submit_label
    if st.button(button_label, type="primary", width="stretch"):
        if selected is None:
            st.warning("Choose a response before checking your reasoning.")
        else:
            selected = str(selected)
            save_draft(draft_group, item.id, widget_key)
            result = evaluate_decision(item.id, selected)
            store_simple_answer(
                responses_key,
                item.id,
                selected,
                f"{score_prefix}:{item.id}",
                bool(result["correct"]),
            )
            st.rerun()

def render_inventory_screen() -> None:
    render_sequential_stage(
        eyebrow="Step 1: What belongs in inventory?",
        header="Screen each item using purpose and ownership",
        introduction=(
            "A reliable count includes merchandise the company owns, even when it is in transit, "
            "and excludes goods owned by others, even when they are physically inside the store."
        ),
        items=COUNT_DECISIONS,
        index_key="sts_count_index",
        responses_key="sts_count_responses",
        score_prefix="count",
        next_stage=2,
        submit_label="Check this item",
    )

def render_quantity_stage() -> None:
    st.markdown('<div class="eyebrow">Step 2: How many owned units remain?</div>', unsafe_allow_html=True)
    st.header("Reconcile the warehouse count to the accounting quantity")
    st.write(
        "Use the evidence already reviewed. The four-unit FOB-destination purchase is already excluded "
        "from the warehouse count. The accounting system shows 44 units on hand."
    )

    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric-box"><strong>{PHYSICAL_COUNT}</strong><span>Warehouse count</span></div>
          <div class="metric-box"><strong>-{CONSIGNED_UNITS}</strong><span>Consigned units inside count</span></div>
          <div class="metric-box"><strong>+{INBOUND_SHIPPING_POINT_UNITS}</strong><span>Owned inbound units</span></div>
          <div class="metric-box"><strong>+{OUTBOUND_DESTINATION_UNITS}</strong><span>Owned outbound units</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    prior_values = dict(st.session_state.sts_quantity_values)
    prior_effect = st.session_state.sts_quantity_effect
    if st.session_state.sts_quantity_submitted:
        result = evaluate_quantity(prior_values, prior_effect)
        for key, label, _amount in QUANTITY_FIELDS:
            field = result["fields"][key]
            render_feedback_row(
                label,
                bool(field["correct"]),
                "Your calculation is correct." if field["correct"] else QUANTITY_HINTS[key],
                f"Submitted {int(field['submitted']):,}",
            )
        render_feedback_row(
            "Account and statement effects",
            bool(result["effect"]["correct"]),
            (
                "You correctly traced the shrinkage through the accounts and financial statements."
                if result["effect"]["correct"]
                else "Shrinkage means fewer goods remain than the accounting system reports. Trace that difference through Inventory, Cost of Goods Sold, total assets, and net income."
            ),
            str(result["effect"]["submitted"]),
        )
        if result["correct"]:
            st.success("The corrected ending quantity is 40 bicycles, revealing four units of shrinkage.")
            st.button("Continue to cost assignment", type="primary", width="stretch", on_click=set_stage, args=(3,))
            return
        st.warning("Revise any quantity or effect below, then check the reconciliation again.")

    draft = dict(st.session_state.sts_drafts["quantity"])
    columns = st.columns(2)
    entered = {}
    for index, (key, label, _expected) in enumerate(QUANTITY_FIELDS):
        widget_key = f"widget_quantity_{key}"
        with columns[index]:
            entered[key] = int(
                st.number_input(
                    label,
                    min_value=0,
                    max_value=500,
                    step=1,
                    value=int(draft.get(key, prior_values.get(key, 0))),
                    key=widget_key,
                    on_change=save_draft,
                    args=("quantity", key, widget_key),
                )
            )
    effect_options = shuffled(QUANTITY_EFFECT_OPTIONS, "quantity-effect")
    effect_key = "widget_quantity_effect"
    effect = st.radio(
        "What is the effect of the inventory shrinkage compared with the records?",
        effect_options,
        index=selected_index(effect_options, draft.get("effect", prior_effect)),
        key=effect_key,
        on_change=save_draft,
        args=("quantity", "effect", effect_key),
    )
    button_label = (
        "Check revised reconciliation"
        if st.session_state.sts_quantity_submitted
        else "Check the reconciliation"
    )
    if st.button(button_label, type="primary", width="stretch"):
        if effect is None:
            st.warning("Choose the account and financial-statement effect before checking.")
        else:
            effect = str(effect)
            answer = {**entered, "effect": effect}
            replace_draft("quantity", answer)
            result = evaluate_quantity(entered, effect)
            for key, _label, _expected in QUANTITY_FIELDS:
                score_key = f"quantity:{key}"
                if score_key not in st.session_state.sts_first_pass or prior_values.get(key) != entered[key]:
                    record_attempt(st.session_state, score_key, bool(result["fields"][key]["correct"]))
            if "quantity:effect" not in st.session_state.sts_first_pass or prior_effect != effect:
                record_attempt(st.session_state, "quantity:effect", bool(result["effect"]["correct"]))
            st.session_state.sts_quantity_values = entered
            st.session_state.sts_quantity_effect = effect
            st.session_state.sts_quantity_submitted = True
            st.rerun()

def render_cost_stage() -> None:
    st.markdown('<div class="eyebrow">Step 3: What are the units worth?</div>', unsafe_allow_html=True)
    st.header("Assign cost using one beginning layer and one purchase layer")
    st.write(escape_dollar_markdown("The physical review established 40 ending units. Now assign the $27,600 total cost available between ending Inventory and Cost of Goods Sold."))
    render_layers()

    prior_values = dict(st.session_state.sts_cost_values)
    if st.session_state.sts_cost_submitted:
        result = evaluate_costing(prior_values)
        for key, label, _amount in COST_FIELDS:
            field = result["fields"][key]
            render_feedback_row(
                label,
                bool(field["correct"]),
                "Your cost assignment is correct." if field["correct"] else COST_HINTS[key],
                f"Submitted {format_currency(field['submitted'])}",
            )
        if result["correct"]:
            st.success(escape_dollar_markdown("Every method reconciles: ending Inventory plus Cost of Goods Sold equals $27,600."))
            st.button("Continue to financial-statement effects", type="primary", width="stretch", on_click=set_stage, args=(4,))
            return
        st.warning("Revise any cost assignment below, then check all three methods again.")

    draft = dict(st.session_state.sts_drafts["cost"])
    fifo_tab, lifo_tab, average_tab = st.tabs(["FIFO", "LIFO", "Average cost"])
    entered = {}

    def cost_input(container, key: str, label: str, maximum: int, step: int) -> int:
        widget_key = f"widget_cost_{key}"
        with container:
            return int(
                st.number_input(
                    label,
                    min_value=0,
                    max_value=maximum,
                    step=step,
                    value=int(draft.get(key, prior_values.get(key, 0))),
                    key=widget_key,
                    on_change=save_draft,
                    args=("cost", key, widget_key),
                )
            )

    with fifo_tab:
        st.caption("FIFO leaves the newest costs in ending inventory.")
    entered["fifo_ending_inventory"] = cost_input(fifo_tab, "fifo_ending_inventory", "FIFO ending Inventory", 100_000, 100)
    entered["fifo_cogs"] = cost_input(fifo_tab, "fifo_cogs", "FIFO cost of goods sold", 100_000, 100)
    with lifo_tab:
        st.caption("LIFO leaves the oldest costs in ending inventory.")
    entered["lifo_ending_inventory"] = cost_input(lifo_tab, "lifo_ending_inventory", "LIFO ending Inventory", 100_000, 100)
    entered["lifo_cogs"] = cost_input(lifo_tab, "lifo_cogs", "LIFO cost of goods sold", 100_000, 100)
    with average_tab:
        st.caption("Weighted average blends the costs of all available units.")
    entered["average_unit_cost"] = cost_input(average_tab, "average_unit_cost", "Weighted-average unit cost", 1_000, 1)
    entered["average_ending_inventory"] = cost_input(average_tab, "average_ending_inventory", "Average-cost ending Inventory", 100_000, 100)
    entered["average_cogs"] = cost_input(average_tab, "average_cogs", "Average-cost cost of goods sold", 100_000, 100)

    button_label = "Check revised cost assignment" if st.session_state.sts_cost_submitted else "Check all three methods"
    if st.button(button_label, type="primary", width="stretch"):
        result = evaluate_costing(entered)
        replace_draft("cost", entered)
        for key, _label, _expected in COST_FIELDS:
            score_key = f"cost:{key}"
            if score_key not in st.session_state.sts_first_pass or prior_values.get(key) != entered[key]:
                record_attempt(st.session_state, score_key, bool(result["fields"][key]["correct"]))
        st.session_state.sts_cost_values = entered
        st.session_state.sts_cost_submitted = True
        st.rerun()

def render_method_table() -> None:
    rows = []
    for result in method_results().values():
        rows.append(
            f"<tr><td>{escape(result.method)}</td><td>{escape(format_currency(result.ending_inventory))}</td>"
            f"<td>{escape(format_currency(result.cost_of_goods_sold))}</td><td>{escape(format_currency(result.gross_profit))}</td></tr>"
        )
    st.markdown(
        f"""
        <table class="method-table">
          <thead><tr><th>Method</th><th>Ending Inventory</th><th>Cost of Goods Sold</th><th>Gross Profit</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
    st.caption(escape_dollar_markdown(f"Net sales are {format_currency(SALES_REVENUE)} under every method."))

def render_reporting_stage() -> None:
    render_method_table()
    render_sequential_stage(
        eyebrow="Step 4: Why do the methods change the statements?",
        header="Explain why the methods produce different financial-statement effects",
        introduction=(
            "Use the cost-flow table as evidence, then explain the concepts that cause the differences. "
            "The costing method does not change the total cost available."
        ),
        items=REPORTING_DECISIONS,
        index_key="sts_reporting_index",
        responses_key="sts_reporting_responses",
        score_prefix="reporting",
        next_stage=5,
        submit_label="Check the reasoning",
    )

def render_analysis_stage() -> None:
    st.markdown('<div class="eyebrow">Step 5: What does inventory performance mean?</div>', unsafe_allow_html=True)
    st.header("Use FIFO amounts to analyze inventory management")
    st.write(
        "Calculate average inventory, inventory turnover, and days in inventory using the FIFO amounts below. "
        "Round inventory turnover to two decimal places and days in inventory to the nearest whole day."
    )
    results = method_results()["FIFO"]
    st.markdown(
        f"""
        <div class="analysis-metric-grid">
          <div class="metric-box"><strong>{format_currency(BEGINNING_UNITS * BEGINNING_UNIT_COST)}</strong><span>Beginning Inventory</span></div>
          <div class="metric-box"><strong>{format_currency(results.ending_inventory)}</strong><span>Ending Inventory</span></div>
          <div class="metric-box"><strong>{format_currency(results.cost_of_goods_sold)}</strong><span>Cost of Goods Sold</span></div>
          <div class="metric-box"><strong>{TURNOVER_BENCHMARK:.2f} times</strong><span>Industry average turnover</span></div>
          <div class="metric-box"><strong>{DAYS_BENCHMARK} days</strong><span>Industry average days in inventory</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prior_values = dict(st.session_state.sts_analysis_values)
    prior_interpretation = st.session_state.sts_analysis_interpretation
    prior_recommendation = st.session_state.sts_analysis_recommendation
    if st.session_state.sts_analysis_submitted:
        result = evaluate_analysis(
            prior_values,
            prior_interpretation,
            prior_recommendation,
        )
        for key, label, _value in ANALYSIS_FIELDS:
            field = result["fields"][key]
            if key == "inventory_turnover":
                submitted_text = f"{float(field['submitted']):.2f} times"
            elif key == "days_in_inventory":
                submitted_text = f"{int(field['submitted'])} days"
            else:
                submitted_text = format_currency(field["submitted"])
            render_feedback_row(
                label,
                bool(field["correct"]),
                "Your calculation and rounding are correct." if field["correct"] else ANALYSIS_HINTS[key],
                f"Submitted {submitted_text}",
            )
        render_feedback_row(
            "Interpretation",
            bool(result["interpretation"]["correct"]),
            (
                "You correctly interpreted both measures against the industry averages."
                if result["interpretation"]["correct"]
                else "Compare both measures with the industry: consider what lower turnover and more days would say about how quickly inventory moves."
            ),
            str(result["interpretation"]["submitted"]),
        )
        render_feedback_row(
            "Management response",
            bool(result["recommendation"]["correct"]),
            (
                "Your recommendation responds directly to the inventory performance evidence."
                if result["recommendation"]["correct"]
                else "Choose an action that investigates the cause of slow-moving inventory before changing future purchasing decisions."
            ),
            str(result["recommendation"]["submitted"]),
        )
        if result["correct"]:
            st.success("The inventory is moving more slowly than the industry averages, so management should investigate the models creating the delay.")
            st.button("Finish the case", type="primary", width="stretch", on_click=set_stage, args=(6,))
            return
        st.warning("Revise any calculation or interpretation below, then check the inventory analysis again.")

    draft = dict(st.session_state.sts_drafts["analysis"])
    columns = st.columns(3)
    entered: dict[str, int | float] = {}
    for index, (key, label, _expected) in enumerate(ANALYSIS_FIELDS):
        widget_key = f"widget_analysis_{key}"
        with columns[index]:
            if key == "inventory_turnover":
                entered[key] = float(
                    st.number_input(
                        label,
                        min_value=0.0,
                        max_value=100.0,
                        step=0.01,
                        format="%.2f",
                        value=float(draft.get(key, prior_values.get(key, 0.0))),
                        key=widget_key,
                        on_change=save_draft,
                        args=("analysis", key, widget_key),
                    )
                )
            else:
                entered[key] = int(
                    st.number_input(
                        label,
                        min_value=0,
                        max_value=1_000_000,
                        step=1,
                        value=int(draft.get(key, prior_values.get(key, 0))),
                        key=widget_key,
                        on_change=save_draft,
                        args=("analysis", key, widget_key),
                    )
                )

    interpretation_options = shuffled(ANALYSIS_INTERPRETATION_OPTIONS, "analysis-interpretation")
    interpretation_key = "widget_analysis_interpretation"
    interpretation = st.radio(
        f"What does Flyer Cycle Works' inventory performance indicate compared with the industry averages of {TURNOVER_BENCHMARK:.2f} times turnover and {DAYS_BENCHMARK} days in inventory?",
        interpretation_options,
        index=selected_index(
            interpretation_options,
            draft.get("interpretation", prior_interpretation),
        ),
        key=interpretation_key,
        on_change=save_draft,
        args=("analysis", "interpretation", interpretation_key),
    )

    recommendation_options = shuffled(ANALYSIS_RECOMMENDATION_OPTIONS, "analysis-recommendation")
    recommendation_key = "widget_analysis_recommendation"
    recommendation = st.radio(
        "Which management response best fits the evidence?",
        recommendation_options,
        index=selected_index(
            recommendation_options,
            draft.get("recommendation", prior_recommendation),
        ),
        key=recommendation_key,
        on_change=save_draft,
        args=("analysis", "recommendation", recommendation_key),
    )
    button_label = (
        "Check revised inventory analysis"
        if st.session_state.sts_analysis_submitted
        else "Check the inventory analysis"
    )
    if st.button(button_label, type="primary", width="stretch"):
        if interpretation is None or recommendation is None:
            st.warning("Complete both interpretations before checking your analysis.")
        else:
            interpretation = str(interpretation)
            recommendation = str(recommendation)
            answer = {
                **entered,
                "interpretation": interpretation,
                "recommendation": recommendation,
            }
            replace_draft("analysis", answer)
            result = evaluate_analysis(entered, interpretation, recommendation)
            for key, _label, _expected in ANALYSIS_FIELDS:
                score_key = f"analysis:{key}"
                if score_key not in st.session_state.sts_first_pass or prior_values.get(key) != entered[key]:
                    record_attempt(st.session_state, score_key, bool(result["fields"][key]["correct"]))
            if "analysis:interpretation" not in st.session_state.sts_first_pass or prior_interpretation != interpretation:
                record_attempt(
                    st.session_state,
                    "analysis:interpretation",
                    bool(result["interpretation"]["correct"]),
                )
            if "analysis:recommendation" not in st.session_state.sts_first_pass or prior_recommendation != recommendation:
                record_attempt(
                    st.session_state,
                    "analysis:recommendation",
                    bool(result["recommendation"]["correct"]),
                )
            st.session_state.sts_analysis_values = entered
            st.session_state.sts_analysis_interpretation = interpretation
            st.session_state.sts_analysis_recommendation = recommendation
            st.session_state.sts_analysis_submitted = True
            st.rerun()

def render_completion() -> None:
    score = score_summary(st.session_state)
    metrics = inventory_metrics("FIFO")
    st.markdown('<div class="eyebrow">Case debrief</div>', unsafe_allow_html=True)
    st.header("The stockroom now supports the statements")
    st.success("Case complete. You traced one inventory count from physical evidence to management analysis.")
    st.markdown(
        """
        <div class="chain">
          <div class="chain-step">Purpose and ownership</div>
          <div class="chain-step">Ending quantity</div>
          <div class="chain-step">Cost assignment</div>
          <div class="chain-step">Account balances and statements</div>
          <div class="chain-step">Turnover and management action</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric-box"><strong>40 units</strong><span>Correct ending quantity</span></div>
          <div class="metric-box"><strong>{format_currency(method_results()["FIFO"].ending_inventory)}</strong><span>FIFO ending Inventory</span></div>
          <div class="metric-box"><strong>{metrics["inventory_turnover"]:.2f} times</strong><span>FIFO turnover</span></div>
          <div class="metric-box"><strong>{metrics["days_in_inventory"]:.0f} days</strong><span>Days in inventory</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "The completed case shows how each inventory decision carries forward. Ownership rules determine "
        "which goods belong in inventory, the physical count establishes the starting quantity, and the "
        "reconciliation identifies shrinkage. The cost-flow method then divides the cost of goods available "
        "for sale between ending Inventory and Cost of Goods Sold, affecting current assets, gross profit, "
        "and net income."
    )
    st.write(
        "Analysis completes the chain. Inventory turnover and days in inventory translate the accounting "
        "results into evidence about how efficiently the company is managing its stock. Comparing those "
        "measures with industry averages helps managers identify whether inventory is moving too slowly and "
        "whether purchasing, pricing, or sales decisions deserve attention."
    )
    st.caption(
        f"First-pass evidence: {score['correct']} of {score['attempted']} attempted checkpoints correct; "
        f"{score['revisions']} revision(s). Final mastery: complete."
    )
    st.caption("Keep this tab or bookmark its current URL if you want to return to the completed case.")
