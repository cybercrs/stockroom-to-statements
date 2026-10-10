"""Known teaching cases used by the actual browser walkthrough."""

from stockroom_to_statements import case_data as data, engine
from stockroom_to_statements.progress import (
    decode_snapshot as decode_snapshot,
    score_summary as score_summary,
)
from browser.navigation import POSITIONS as POSITIONS


def choice(items, check, final="Continue"):
    return {"kind": "choice", "items": items, "check": check, "final": final}


def numbers(values, fields, prefix, check, final=None, radios=()):
    return {
        "kind": "numbers",
        "values": values,
        "fields": fields,
        "prefix": prefix,
        "check": check,
        "final": final,
        "radios": radios,
    }


START = "Begin the inventory review"
PLAN = [
    choice(data.COUNT_DECISIONS, "Check this item"),
    numbers(
        engine.expected_quantity_values(),
        data.QUANTITY_FIELDS,
        "widget_quantity_",
        "Check the reconciliation",
        "Continue to cost assignment",
        [("widget_quantity_effect", data.QUANTITY_EFFECT_CORRECT)],
    ),
    numbers(
        engine.expected_cost_values(),
        data.COST_FIELDS,
        "widget_cost_",
        "Check all three methods",
        "Continue to financial-statement effects",
    ),
    choice(data.REPORTING_DECISIONS, "Check the reasoning"),
    numbers(
        engine.expected_analysis_values(),
        data.ANALYSIS_FIELDS,
        "widget_analysis_",
        "Check the inventory analysis",
        "Finish the case",
        [
            ("widget_analysis_interpretation", data.ANALYSIS_INTERPRETATION_CORRECT),
            ("widget_analysis_recommendation", data.ANALYSIS_RECOMMENDATION_CORRECT),
        ],
    ),
]
