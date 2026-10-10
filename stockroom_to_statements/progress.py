"""Compact, validated, non-identifying progress snapshots."""

from __future__ import annotations

import base64
import json
import secrets
import zlib
from collections.abc import MutableMapping
from typing import Any

from stockroom_to_statements.case_data import (
    ANALYSIS_FIELDS,
    ANALYSIS_INTERPRETATION_OPTIONS,
    ANALYSIS_RECOMMENDATION_OPTIONS,
    COST_FIELDS,
    COUNT_DECISIONS,
    QUANTITY_EFFECT_OPTIONS,
    QUANTITY_FIELDS,
    REPORTING_DECISIONS,
)
from stockroom_to_statements.engine import (
    evaluate_analysis,
    evaluate_costing,
    evaluate_quantity,
)


SNAPSHOT_PARAM = "progress"
SNAPSHOT_VERSION = 2
MAX_TOKEN_LENGTH = 16_000
MAX_JSON_BYTES = 32_000


def activity_defaults() -> dict[str, Any]:
    return {
        "sts_stage": 0,
        "sts_shuffle_seed": secrets.randbits(63),
        "sts_drafts": {
            "count": {},
            "quantity": {},
            "cost": {},
            "reporting": {},
            "analysis": {},
        },
        "sts_count_index": 0,
        "sts_count_responses": {},
        "sts_quantity_values": {},
        "sts_quantity_effect": "",
        "sts_quantity_submitted": False,
        "sts_cost_values": {},
        "sts_cost_submitted": False,
        "sts_reporting_index": 0,
        "sts_reporting_responses": {},
        "sts_analysis_values": {},
        "sts_analysis_interpretation": "",
        "sts_analysis_recommendation": "",
        "sts_analysis_submitted": False,
        "sts_attempts": {},
        "sts_first_pass": {},
        "sts_scroll_to_top": False,
    }


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")


def _decode(token: str) -> object:
    padding = "=" * (-len(token) % 4)
    compressed = base64.b64decode(token + padding, altchars=b"-_", validate=True)
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(compressed, MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES or decompressor.unconsumed_tail:
        raise ValueError("Snapshot is too large")
    raw += decompressor.flush(MAX_JSON_BYTES + 1 - len(raw))
    if len(raw) > MAX_JSON_BYTES or decompressor.unused_data:
        raise ValueError("Snapshot is invalid")
    return json.loads(raw.decode("utf-8"))


def _require_index(value: object, count: int) -> int:
    if type(value) is not int or not 0 <= value < count:
        raise ValueError("Invalid activity index")
    return value


def _answer_prefix(raw: object, items) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("Answers must be an object")
    ids = [item.id for item in items]
    if set(raw) != set(ids[: len(raw)]):
        raise ValueError("Answers must follow the activity order")
    normalized = {}
    for item in items[: len(raw)]:
        value = raw[item.id]
        if not isinstance(value, str) or value not in item.options:
            raise ValueError("Unknown answer")
        normalized[item.id] = value
    return normalized


def _validate_number_map(raw: object, fields, *, allow_float: bool) -> dict[str, int | float]:
    if not isinstance(raw, dict):
        raise ValueError("Number responses must be an object")
    keys = {key for key, _label, _expected in fields}
    if set(raw) - keys:
        raise ValueError("Unknown number response")
    normalized: dict[str, int | float] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Invalid number response")
        if not allow_float and type(value) is not int:
            raise ValueError("Whole-dollar response required")
        if not 0 <= value <= 10_000_000:
            raise ValueError("Number response is out of range")
        normalized[key] = value
    return normalized


def _validate_choice_draft(raw: object, items, current_index: int) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("Choice drafts must be an object")
    ids = [item.id for item in items]
    if set(raw) - set(ids[: current_index + 1]):
        raise ValueError("Choice drafts are out of sequence")
    normalized = {}
    for item in items:
        if item.id not in raw:
            continue
        value = raw[item.id]
        if not isinstance(value, str) or value not in item.options:
            raise ValueError("Invalid draft choice")
        normalized[item.id] = value
    return normalized


def _validate_combined_draft(
    raw: object,
    fields,
    choices: dict[str, tuple[str, ...]],
    *,
    allow_float: bool,
) -> dict[str, int | float | str]:
    if not isinstance(raw, dict):
        raise ValueError("Combined drafts must be an object")
    numeric_keys = {key for key, _label, _expected in fields}
    if set(raw) - numeric_keys - set(choices):
        raise ValueError("Unknown combined draft")
    normalized: dict[str, int | float | str] = _validate_number_map(
        {key: value for key, value in raw.items() if key in numeric_keys},
        fields,
        allow_float=allow_float,
    )
    for key, options in choices.items():
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, str) or value not in options:
            raise ValueError("Invalid combined draft choice")
        normalized[key] = value
    return normalized


def _valid_score_keys() -> set[str]:
    keys = {f"count:{item.id}" for item in COUNT_DECISIONS}
    keys |= {f"quantity:{key}" for key, _label, _expected in QUANTITY_FIELDS}
    keys.add("quantity:effect")
    keys |= {f"cost:{key}" for key, _label, _expected in COST_FIELDS}
    keys |= {f"reporting:{item.id}" for item in REPORTING_DECISIONS}
    keys |= {f"analysis:{key}" for key, _label, _expected in ANALYSIS_FIELDS}
    keys |= {"analysis:interpretation", "analysis:recommendation"}
    return keys


def _all_correct(responses: dict[str, str], items) -> bool:
    return len(responses) == len(items) and all(responses[item.id] == item.correct for item in items)


def validate_snapshot(raw: object) -> dict[str, Any]:
    expected_keys = {
        "v", "s", "o", "dr", "ci", "cr", "qv", "qe", "qs", "cv", "cs",
        "ri", "rr", "av", "ai", "am", "as", "at", "fp",
    }
    if not isinstance(raw, dict) or set(raw) != expected_keys or raw["v"] != SNAPSHOT_VERSION:
        raise ValueError("Unsupported snapshot")

    stage = raw["s"]
    if type(stage) is not int or not 0 <= stage <= 6:
        raise ValueError("Invalid stage")

    shuffle_seed = raw["o"]
    if type(shuffle_seed) is not int or not 0 <= shuffle_seed < 2**63:
        raise ValueError("Invalid shuffle seed")

    count_index = _require_index(raw["ci"], len(COUNT_DECISIONS))
    reporting_index = _require_index(raw["ri"], len(REPORTING_DECISIONS))
    count_responses = _answer_prefix(raw["cr"], COUNT_DECISIONS)
    reporting_responses = _answer_prefix(raw["rr"], REPORTING_DECISIONS)

    quantity_submitted = raw["qs"]
    cost_submitted = raw["cs"]
    analysis_submitted = raw["as"]
    if any(type(value) is not bool for value in (quantity_submitted, cost_submitted, analysis_submitted)):
        raise ValueError("Invalid submission status")

    quantity_values = _validate_number_map(raw["qv"], QUANTITY_FIELDS, allow_float=False)
    cost_values = _validate_number_map(raw["cv"], COST_FIELDS, allow_float=False)
    analysis_values = _validate_number_map(raw["av"], ANALYSIS_FIELDS, allow_float=True)

    quantity_effect = raw["qe"]
    analysis_interpretation = raw["ai"]
    analysis_recommendation = raw["am"]
    if not isinstance(quantity_effect, str) or quantity_effect not in ("", *QUANTITY_EFFECT_OPTIONS):
        raise ValueError("Invalid quantity effect")
    if not isinstance(analysis_interpretation, str) or analysis_interpretation not in (
        "", *ANALYSIS_INTERPRETATION_OPTIONS
    ):
        raise ValueError("Invalid analysis interpretation")
    if not isinstance(analysis_recommendation, str) or analysis_recommendation not in (
        "", *ANALYSIS_RECOMMENDATION_OPTIONS
    ):
        raise ValueError("Invalid analysis recommendation")

    raw_drafts = raw["dr"]
    if not isinstance(raw_drafts, dict) or set(raw_drafts) != {"c", "q", "k", "r", "a"}:
        raise ValueError("Invalid draft groups")
    drafts = {
        "count": _validate_choice_draft(raw_drafts["c"], COUNT_DECISIONS, count_index),
        "quantity": _validate_combined_draft(
            raw_drafts["q"],
            QUANTITY_FIELDS,
            {"effect": QUANTITY_EFFECT_OPTIONS},
            allow_float=False,
        ),
        "cost": _validate_combined_draft(
            raw_drafts["k"], COST_FIELDS, {}, allow_float=False
        ),
        "reporting": _validate_choice_draft(
            raw_drafts["r"], REPORTING_DECISIONS, reporting_index
        ),
        "analysis": _validate_combined_draft(
            raw_drafts["a"],
            ANALYSIS_FIELDS,
            {
                "interpretation": ANALYSIS_INTERPRETATION_OPTIONS,
                "recommendation": ANALYSIS_RECOMMENDATION_OPTIONS,
            },
            allow_float=True,
        ),
    }
    minimum_stages = {"count": 1, "quantity": 2, "cost": 3, "reporting": 4, "analysis": 5}
    for group, minimum_stage in minimum_stages.items():
        if stage < minimum_stage and drafts[group]:
            raise ValueError("Future draft is not allowed")

    if quantity_submitted and (
        set(quantity_values) != {key for key, _label, _expected in QUANTITY_FIELDS}
        or not quantity_effect
    ):
        raise ValueError("Submitted quantity work is incomplete")
    if cost_submitted and set(cost_values) != {key for key, _label, _expected in COST_FIELDS}:
        raise ValueError("Submitted costing work is incomplete")
    if analysis_submitted and (
        set(analysis_values) != {key for key, _label, _expected in ANALYSIS_FIELDS}
        or not analysis_interpretation
        or not analysis_recommendation
    ):
        raise ValueError("Submitted analysis is incomplete")

    if not isinstance(raw["at"], dict) or not isinstance(raw["fp"], dict):
        raise ValueError("Invalid score history")
    valid_score_keys = _valid_score_keys()
    attempts = {}
    for key, value in raw["at"].items():
        if key not in valid_score_keys or type(value) is not int or not 1 <= value <= 99:
            raise ValueError("Invalid attempt history")
        attempts[key] = value
    first_pass = {}
    for key, value in raw["fp"].items():
        if key not in valid_score_keys or type(value) is not bool:
            raise ValueError("Invalid first-pass history")
        first_pass[key] = value

    if stage == 0 and any(
        (
            count_responses,
            quantity_values,
            quantity_effect,
            cost_values,
            reporting_responses,
            analysis_values,
            analysis_interpretation,
            analysis_recommendation,
        )
    ):
        raise ValueError("Briefing cannot contain activity answers")
    if stage < 2 and (quantity_values or quantity_effect or quantity_submitted):
        raise ValueError("Quantity work appears too early")
    if stage < 3 and (cost_values or cost_submitted):
        raise ValueError("Cost work appears too early")
    if stage < 4 and reporting_responses:
        raise ValueError("Reporting work appears too early")
    if stage < 5 and (
        analysis_values or analysis_interpretation or analysis_recommendation or analysis_submitted
    ):
        raise ValueError("Analysis appears too early")

    if stage >= 2 and not _all_correct(count_responses, COUNT_DECISIONS):
        raise ValueError("Inventory screen is incomplete")
    if stage >= 3:
        quantity_result = evaluate_quantity(quantity_values, quantity_effect)
        if not quantity_submitted or not quantity_result["correct"]:
            raise ValueError("Quantity reconciliation is unresolved")
    if stage >= 4:
        cost_result = evaluate_costing(cost_values)
        if not cost_submitted or not cost_result["correct"]:
            raise ValueError("Costing work is unresolved")
    if stage >= 5 and not _all_correct(reporting_responses, REPORTING_DECISIONS):
        raise ValueError("Statement effects are incomplete")
    if stage >= 6:
        analysis_result = evaluate_analysis(
            analysis_values,
            analysis_interpretation,
            analysis_recommendation,
        )
        if not analysis_submitted or not analysis_result["correct"]:
            raise ValueError("Inventory analysis is unresolved")

    for item in COUNT_DECISIONS[:count_index]:
        if count_responses.get(item.id) != item.correct:
            raise ValueError("A prior inventory-screen response is unresolved")
    for item in REPORTING_DECISIONS[:reporting_index]:
        if reporting_responses.get(item.id) != item.correct:
            raise ValueError("A prior statement response is unresolved")

    if stage == 1 and len(count_responses) not in {count_index, count_index + 1}:
        raise ValueError("Inventory-screen position is inconsistent")
    if stage >= 2 and count_index != len(COUNT_DECISIONS) - 1:
        raise ValueError("Completed inventory-screen position is invalid")
    if stage == 4 and len(reporting_responses) not in {reporting_index, reporting_index + 1}:
        raise ValueError("Statement position is inconsistent")
    if stage >= 5 and reporting_index != len(REPORTING_DECISIONS) - 1:
        raise ValueError("Completed statement position is invalid")

    return {
        "sts_stage": stage,
        "sts_shuffle_seed": shuffle_seed,
        "sts_drafts": drafts,
        "sts_count_index": count_index,
        "sts_count_responses": count_responses,
        "sts_quantity_values": quantity_values,
        "sts_quantity_effect": quantity_effect,
        "sts_quantity_submitted": quantity_submitted,
        "sts_cost_values": cost_values,
        "sts_cost_submitted": cost_submitted,
        "sts_reporting_index": reporting_index,
        "sts_reporting_responses": reporting_responses,
        "sts_analysis_values": analysis_values,
        "sts_analysis_interpretation": analysis_interpretation,
        "sts_analysis_recommendation": analysis_recommendation,
        "sts_analysis_submitted": analysis_submitted,
        "sts_attempts": attempts,
        "sts_first_pass": first_pass,
    }


def snapshot_from_state(state: MutableMapping[str, Any]) -> dict[str, Any]:
    return {
        "v": SNAPSHOT_VERSION,
        "s": state["sts_stage"],
        "o": state["sts_shuffle_seed"],
        "dr": {
            "c": state["sts_drafts"]["count"],
            "q": state["sts_drafts"]["quantity"],
            "k": state["sts_drafts"]["cost"],
            "r": state["sts_drafts"]["reporting"],
            "a": state["sts_drafts"]["analysis"],
        },
        "ci": state["sts_count_index"],
        "cr": state["sts_count_responses"],
        "qv": state["sts_quantity_values"],
        "qe": state["sts_quantity_effect"],
        "qs": state["sts_quantity_submitted"],
        "cv": state["sts_cost_values"],
        "cs": state["sts_cost_submitted"],
        "ri": state["sts_reporting_index"],
        "rr": state["sts_reporting_responses"],
        "av": state["sts_analysis_values"],
        "ai": state["sts_analysis_interpretation"],
        "am": state["sts_analysis_recommendation"],
        "as": state["sts_analysis_submitted"],
        "at": state["sts_attempts"],
        "fp": state["sts_first_pass"],
    }


def encode_state(state: MutableMapping[str, Any]) -> str:
    return _encode(snapshot_from_state(state))


def decode_snapshot(token: object) -> dict[str, Any] | None:
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    try:
        return validate_snapshot(_decode(token))
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, zlib.error):
        return None


def restore_session_state(state: MutableMapping[str, Any], token: object) -> bool:
    restored = decode_snapshot(token)
    if restored is None:
        return False
    state.update(restored)
    return True


def sync_progress_query(state: MutableMapping[str, Any], query_params: MutableMapping[str, Any]) -> None:
    token = encode_state(state)
    current = query_params.get(SNAPSHOT_PARAM)
    if isinstance(current, list):
        current = current[0] if current else None
    if current != token:
        query_params[SNAPSHOT_PARAM] = token


def reset_saved_progress(state: MutableMapping[str, Any], query_params: MutableMapping[str, Any]) -> None:
    for key in list(state):
        if key.startswith("sts_") or key.startswith("widget_"):
            del state[key]
    state.update(activity_defaults())
    query_params[SNAPSHOT_PARAM] = encode_state(state)


def record_attempt(state: MutableMapping[str, Any], score_key: str, correct: bool) -> None:
    attempts = dict(state["sts_attempts"])
    first_pass = dict(state["sts_first_pass"])
    attempts[score_key] = attempts.get(score_key, 0) + 1
    if score_key not in first_pass:
        first_pass[score_key] = bool(correct)
    state["sts_attempts"] = attempts
    state["sts_first_pass"] = first_pass


def score_summary(state: MutableMapping[str, Any]) -> dict[str, int]:
    first_pass = state.get("sts_first_pass", {})
    attempts = state.get("sts_attempts", {})
    return {
        "correct": sum(1 for value in first_pass.values() if value),
        "attempted": len(first_pass),
        "total": len(_valid_score_keys()),
        "revisions": sum(max(0, value - 1) for value in attempts.values()),
    }
