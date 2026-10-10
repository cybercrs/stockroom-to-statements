"""App-specific reached pages; review never changes the canonical snapshot."""

from stockroom_to_statements.case_data import COUNT_DECISIONS, REPORTING_DECISIONS
from stockroom_to_statements import engine

VIEW_KEY = "sts_browser_view"
VIEW_PARAM = "view"
STAGE_KEY = "sts_stage"
SCROLL_KEY = "sts_scroll_to_top"
RENDERERS = (
    "render_briefing",
    "render_inventory_screen",
    "render_quantity_stage",
    "render_cost_stage",
    "render_reporting_stage",
    "render_analysis_stage",
    "render_completion",
)
GROUPS = {
    1: (COUNT_DECISIONS, "sts_count_index", "sts_count_responses"),
    4: (REPORTING_DECISIONS, "sts_reporting_index", "sts_reporting_responses"),
}
POSITIONS = [(0, None, 0)]
for stage in range(1, len(RENDERERS) - 1):
    group = GROUPS.get(stage)
    POSITIONS.extend(
        (stage, group[1] if group else None, index)
        for index in range(len(group[0]) if group else 1)
    )
POSITIONS.append((len(RENDERERS) - 1, None, 0))


def frontier(state):
    stage = state[STAGE_KEY]
    key = GROUPS[stage][1] if stage in GROUPS else None
    return POSITIONS.index((stage, key, state[key] if key else 0))


def restore_view(state, raw):
    try:
        view = int(raw) if isinstance(raw, str) else -1
    except ValueError:
        view = -1
    state[VIEW_KEY] = view if 0 <= view <= frontier(state) else frontier(state)


def move(state, direction):
    if direction not in (-1, 1):
        raise ValueError("Direction must be Back or Forward")
    target = state[VIEW_KEY] + direction
    if not 0 <= target <= frontier(state):
        return False
    state[VIEW_KEY] = target
    state[SCROLL_KEY] = True
    return True


def can_advance(state):
    if state[VIEW_KEY] != frontier(state):
        return False
    stage = state[STAGE_KEY]
    if stage == 0:
        return True
    if stage == 2:
        return (
            state["sts_quantity_submitted"]
            and engine.evaluate_quantity(
                state["sts_quantity_values"], state["sts_quantity_effect"]
            )["correct"]
        )
    if stage == 3:
        return (
            state["sts_cost_submitted"]
            and engine.evaluate_costing(state["sts_cost_values"])["correct"]
        )
    if stage == 5:
        return (
            state["sts_analysis_submitted"]
            and engine.evaluate_analysis(
                state["sts_analysis_values"],
                state["sts_analysis_interpretation"],
                state["sts_analysis_recommendation"],
            )["correct"]
        )
    if stage not in GROUPS:
        return False
    items, key, responses = GROUPS[stage]
    item = items[state[key]]
    return state[responses].get(item.id) == item.correct


def advance(state):
    if not can_advance(state):
        return False
    target = state[VIEW_KEY] + 1
    stage, key, index = POSITIONS[target]
    state[STAGE_KEY] = stage
    if key:
        state[key] = index
    state[VIEW_KEY] = target
    state[SCROLL_KEY] = True
    return True
