"""Capture unchanged Python teaching screens and independent native parity fixtures."""

from __future__ import annotations
import hashlib
import json
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from browser.build import shared_source  # noqa: E402
from browser import navigation  # noqa: E402
from stockroom_to_statements import case_data as case, engine, progress  # noqa: E402


class State(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class Container:
    def __init__(self, recorder, node):
        self.recorder, self.node = recorder, node

    def __enter__(self):
        self.recorder.stack.append(self.node["children"])
        return self

    def __exit__(self, *args):
        self.recorder.stack.pop()

    def metric(self, label, value, **kwargs):
        self.node["children"].append(
            {"kind": "metric", "label": label, "value": value, **kwargs}
        )


class Recorder:
    def __init__(self):
        self.session_state = State()
        self.stack = [[]]

    def node(self, kind, **kwargs):
        item = {"kind": kind, **kwargs}
        self.stack[-1].append(item)
        return item

    def set_page_config(self, **kwargs):
        pass

    def markdown(self, text, unsafe_allow_html=False):
        self.node(
            "html" if unsafe_allow_html else "markdown",
            text=text.strip().replace(r"\$", "$"),
        )

    def __getattr__(self, kind):
        if kind in {
            "header",
            "subheader",
            "write",
            "success",
            "warning",
            "info",
            "caption",
        }:
            return lambda text: self.node(kind, text=str(text).replace(r"\$", "$"))
        raise AttributeError(kind)

    def dataframe(self, rows, **kwargs):
        self.node("table", rows=rows)

    def progress(self, value, text):
        self.node("progress", value=value, text=text)

    def radio(self, label, options, **kwargs):
        self.node(
            "radio", label=label.replace(r"\$", "$"), options=options, key=kwargs["key"]
        )
        index = kwargs.get("index")
        return options[index] if index is not None else None

    def number_input(self, label, **kwargs):
        self.node(
            "number",
            label=label,
            key=kwargs["key"],
            min=kwargs["min_value"],
            max=kwargs["max_value"],
            step=kwargs["step"],
            decimal=isinstance(kwargs["step"], float),
        )
        return kwargs.get("value", 0)

    def button(self, label, **kwargs):
        self.node("button", label=label, key=kwargs.get("key"))
        return False

    def columns(self, count):
        node = self.node("columns", children=[])
        for _ in range(count if isinstance(count, int) else len(count)):
            node["children"].append({"kind": "column", "children": []})
        return [Container(self, x) for x in node["children"]]

    def tabs(self, labels):
        node = self.node(
            "tabs",
            children=[{"kind": "tab", "label": x, "children": []} for x in labels],
        )
        return [Container(self, x) for x in node["children"]]

    def expander(self, label):
        return Container(self, self.node("details", label=label, children=[]))

    @contextmanager
    def capture(self):
        self.stack = [[]]
        yield self.stack[0]


CHOICE = [
    {
        "stage": 1,
        "prefix": "count",
        "draft": "c",
        "indexKey": "ci",
        "responseKey": "cr",
        "items": [asdict(x) for x in case.COUNT_DECISIONS],
        "salt": "count-options:",
    },
    {
        "stage": 4,
        "prefix": "reporting",
        "draft": "r",
        "indexKey": "ri",
        "responseKey": "rr",
        "items": [asdict(x) for x in case.REPORTING_DECISIONS],
        "salt": "reporting-options:",
    },
]
NUMBERS = [
    {
        "stage": 2,
        "prefix": "quantity",
        "draft": "q",
        "valuesKey": "qv",
        "submittedKey": "qs",
        "fields": case.QUANTITY_FIELDS,
        "expected": engine.expected_quantity_values(),
        "allowFloat": False,
        "choices": [
            {
                "key": "effect",
                "stateKey": "qe",
                "options": case.QUANTITY_EFFECT_OPTIONS,
                "correct": case.QUANTITY_EFFECT_CORRECT,
                "salt": "quantity-effect",
                "label": "Account and statement effects",
            }
        ],
    },
    {
        "stage": 3,
        "prefix": "cost",
        "draft": "k",
        "valuesKey": "cv",
        "submittedKey": "cs",
        "fields": case.COST_FIELDS,
        "expected": engine.expected_cost_values(),
        "allowFloat": False,
        "choices": [],
    },
    {
        "stage": 5,
        "prefix": "analysis",
        "draft": "a",
        "valuesKey": "av",
        "submittedKey": "as",
        "fields": case.ANALYSIS_FIELDS,
        "expected": engine.expected_analysis_values(),
        "allowFloat": True,
        "choices": [
            {
                "key": "interpretation",
                "stateKey": "ai",
                "options": case.ANALYSIS_INTERPRETATION_OPTIONS,
                "correct": case.ANALYSIS_INTERPRETATION_CORRECT,
                "salt": "analysis-interpretation",
                "label": "Interpretation",
            },
            {
                "key": "recommendation",
                "stateKey": "am",
                "options": case.ANALYSIS_RECOMMENDATION_OPTIONS,
                "correct": case.ANALYSIS_RECOMMENDATION_CORRECT,
                "salt": "analysis-recommendation",
                "label": "Management response",
            },
        ],
    },
]


def state_at(stage, index=0, status="unanswered"):
    state = State(progress.activity_defaults())
    state.sts_shuffle_seed = 0
    state.sts_stage = stage
    for group in CHOICE:
        prefix = group["prefix"]
        items = group["items"]
        state[f"sts_{prefix}_index"] = (
            len(items) - 1
            if group["stage"] < stage
            else index
            if group["stage"] == stage
            else 0
        )
        state[f"sts_{prefix}_responses"] = {
            x["id"]: x["correct"]
            if group["stage"] < stage or i < index or status == "correct"
            else next(o for o in x["options"] if o != x["correct"])
            for i, x in enumerate(items)
            if group["stage"] < stage
            or (
                group["stage"] == stage
                and (i < index or (i == index and status != "unanswered"))
            )
        }
    for group in NUMBERS:
        if group["stage"] < stage or (
            group["stage"] == stage and status != "unanswered"
        ):
            good = group["stage"] < stage or status == "correct"
            prefix = group["prefix"]
            state[f"sts_{prefix}_values"] = (
                group["expected"] if good else {k: 0 for k in group["expected"]}
            )
            state[f"sts_{prefix}_submitted"] = True
            for choice in group["choices"]:
                state[f"sts_{prefix}_{choice['key']}"] = (
                    choice["correct"]
                    if good
                    else next(x for x in choice["options"] if x != choice["correct"])
                )
    return state


def export():
    recorder = Recorder()
    namespace = {}
    with patch.dict(sys.modules, {"streamlit": recorder}):
        exec(compile(shared_source(), "original_renderer", "exec"), namespace)
    namespace["render_feedback_row"] = (
        lambda label, correct, detail, value="": recorder.node(
            "feedback", label=label, correct=correct, detail=detail, value=value
        )
    )
    positions = [
        {"stage": stage, "index": i} for stage, _key, i in navigation.POSITIONS
    ]
    screens = []
    for pos in positions:
        variants = {}
        for status in ["unanswered", "wrong", "correct"]:
            recorder.session_state = state_at(**pos, status=status)
            with recorder.capture() as events:
                namespace[navigation.RENDERERS[pos["stage"]]]()
            variants[status] = events
        screens.append({**pos, "variants": variants})
    with recorder.capture() as hero:
        namespace["render_hero"]()
    defaults = progress.activity_defaults()
    defaults["sts_shuffle_seed"] = 0
    facts = {
        name: getattr(case, name)
        for name in [
            "BEGINNING_UNITS",
            "BEGINNING_UNIT_COST",
            "PURCHASE_UNITS",
            "PURCHASE_UNIT_COST",
            "SALES_REVENUE",
            "PHYSICAL_COUNT",
            "CONSIGNED_UNITS",
            "INBOUND_SHIPPING_POINT_UNITS",
            "OUTBOUND_DESTINATION_UNITS",
            "INBOUND_DESTINATION_UNITS",
            "RECORDS_EXPECTED_UNITS",
        ]
    }
    data = {
        "title": "Stockroom to Statements",
        "slug": "stockroom-to-statements",
        "statePrefix": "sts",
        "source": "eb99706710332f5b4d3eefcffbe522af931101fc",
        "seedKey": "o",
        "draftKey": "dr",
        "baseVersion": 2,
        "extensionVersion": 3,
        "defaults": progress.snapshot_from_state(defaults),
        "groups": CHOICE,
        "numbers": NUMBERS,
        "positions": positions,
        "screens": screens,
        "hero": hero,
        "stages": namespace["STAGE_LABELS"],
        "facts": facts,
    }
    here = Path(__file__).resolve().parent
    (here / "content.js").write_text(
        "// Generated without modifying original Python teaching sources.\nexport const DATA = "
        + json.dumps(data, separators=(",", ":"), ensure_ascii=True)
        + ";\n"
    )
    (here / "original.css").write_text(
        namespace["APP_CSS"].replace("<style>", "").replace("</style>", "").strip()
        + "\n"
    )
    fixtures = {
        "calculations": {
            "quantity": engine.quantity_reconciliation(),
            "available": engine.goods_available(),
            "methods": {k: asdict(v) for k, v in engine.method_results().items()},
            "metrics": {
                k: engine.inventory_metrics(k) for k in engine.method_results()
            },
            "expected": {x["prefix"]: x["expected"] for x in NUMBERS},
        },
        "snapshots": [],
        "shuffles": [],
    }
    for stage in range(7):
        state = state_at(stage, status="wrong" if stage in range(1, 6) else "correct")
        wire = progress.snapshot_from_state(state)
        progress.validate_snapshot(wire)
        fixtures["snapshots"].append(
            {"token": progress.encode_state(state), "payload": wire}
        )
    saved_draft = state_at(3)
    saved_draft.sts_shuffle_seed = 2**63 - 1
    saved_draft.sts_drafts["cost"] = {
        "fifo_ending_inventory": 6000,
        "average_unit_cost": 138,
    }
    fixtures["snapshots"].append(
        {
            "token": progress.encode_state(saved_draft),
            "payload": progress.snapshot_from_state(saved_draft),
            "seed": str(2**63 - 1),
        }
    )
    for seed in [0, 1, 42, 2**53 + 1, 2**63 - 1]:
        recorder.session_state.sts_shuffle_seed = seed
        for group in CHOICE:
            for item in group["items"]:
                salt = group["salt"] + item["id"]
                fixtures["shuffles"].append(
                    {
                        "seed": str(seed),
                        "input": item["options"],
                        "salt": salt,
                        "output": namespace["shuffled"](item["options"], salt),
                    }
                )
        for group in NUMBERS:
            for choice in group["choices"]:
                fixtures["shuffles"].append(
                    {
                        "seed": str(seed),
                        "input": choice["options"],
                        "salt": choice["salt"],
                        "output": namespace["shuffled"](
                            choice["options"], choice["salt"]
                        ),
                    }
                )
    (here / "tests").mkdir(exist_ok=True)
    (here / "tests/python-oracles.json").write_text(
        json.dumps(fixtures, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "pages": len(positions),
                "variants": len(screens) * 3,
                "generated_sha256": {
                    name: hashlib.sha256((here / name).read_bytes()).hexdigest()
                    for name in ["content.js", "original.css"]
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    export()
