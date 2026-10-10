"""Pure calculations and answer evaluation for Stockroom to Statements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from stockroom_to_statements.case_data import (
    ANALYSIS_FIELDS,
    ANALYSIS_INTERPRETATION_CORRECT,
    ANALYSIS_RECOMMENDATION_CORRECT,
    BEGINNING_UNIT_COST,
    BEGINNING_UNITS,
    COST_FIELDS,
    COUNT_DECISIONS,
    INBOUND_DESTINATION_UNITS,
    INBOUND_SHIPPING_POINT_UNITS,
    PHYSICAL_COUNT,
    PURCHASE_UNIT_COST,
    PURCHASE_UNITS,
    QUANTITY_EFFECT_CORRECT,
    QUANTITY_FIELDS,
    RECORDS_EXPECTED_UNITS,
    REPORTING_DECISIONS,
    SALES_REVENUE,
    CONSIGNED_UNITS,
    OUTBOUND_DESTINATION_UNITS,
)


@dataclass(frozen=True)
class MethodResult:
    method: str
    ending_inventory: int
    cost_of_goods_sold: int
    gross_profit: int


def format_currency(value: int | float) -> str:
    rounded = round(value)
    if rounded < 0:
        return f"-${abs(rounded):,.0f}"
    return f"${rounded:,.0f}"


def decision_by_id(item_id: str):
    for collection in (COUNT_DECISIONS, REPORTING_DECISIONS):
        for item in collection:
            if item.id == item_id:
                return item
    raise KeyError(item_id)


def evaluate_decision(item_id: str, selected: str) -> dict[str, object]:
    item = decision_by_id(item_id)
    return {
        "correct": selected == item.correct,
        "selected": selected,
        "expected": item.correct,
        "explanation": item.explanation,
        "account_effect": item.account_effect,
        "statement_effect": item.statement_effect,
    }


def quantity_reconciliation() -> dict[str, int]:
    ending_units = (
        PHYSICAL_COUNT
        - CONSIGNED_UNITS
        + INBOUND_SHIPPING_POINT_UNITS
        + OUTBOUND_DESTINATION_UNITS
    )
    return {
        "physical_count": PHYSICAL_COUNT,
        "less_consigned": CONSIGNED_UNITS,
        "add_inbound_shipping_point": INBOUND_SHIPPING_POINT_UNITS,
        "add_outbound_destination": OUTBOUND_DESTINATION_UNITS,
        "exclude_inbound_destination": INBOUND_DESTINATION_UNITS,
        "ending_units": ending_units,
        "records_expected_units": RECORDS_EXPECTED_UNITS,
        "shrinkage_units": RECORDS_EXPECTED_UNITS - ending_units,
    }


def goods_available() -> dict[str, int]:
    beginning_cost = BEGINNING_UNITS * BEGINNING_UNIT_COST
    purchase_cost = PURCHASE_UNITS * PURCHASE_UNIT_COST
    return {
        "units": BEGINNING_UNITS + PURCHASE_UNITS,
        "cost": beginning_cost + purchase_cost,
        "beginning_cost": beginning_cost,
        "purchase_cost": purchase_cost,
    }


def method_results() -> dict[str, MethodResult]:
    available = goods_available()
    ending_units = quantity_reconciliation()["ending_units"]
    average_unit_cost = available["cost"] / available["units"]

    fifo_ending = ending_units * PURCHASE_UNIT_COST
    lifo_ending = ending_units * BEGINNING_UNIT_COST
    average_ending = round(ending_units * average_unit_cost)

    results = {
        "FIFO": MethodResult(
            "FIFO",
            fifo_ending,
            available["cost"] - fifo_ending,
            SALES_REVENUE - (available["cost"] - fifo_ending),
        ),
        "LIFO": MethodResult(
            "LIFO",
            lifo_ending,
            available["cost"] - lifo_ending,
            SALES_REVENUE - (available["cost"] - lifo_ending),
        ),
        "Average cost": MethodResult(
            "Average cost",
            average_ending,
            available["cost"] - average_ending,
            SALES_REVENUE - (available["cost"] - average_ending),
        ),
    }
    return results


def expected_quantity_values() -> dict[str, int]:
    reconciliation = quantity_reconciliation()
    return {key: reconciliation[key] for key, _label, _expected in QUANTITY_FIELDS}


def evaluate_quantity(values: Mapping[str, int], effect: str) -> dict[str, object]:
    expected = expected_quantity_values()
    fields = {
        key: {
            "submitted": int(values.get(key, 0)),
            "expected": amount,
            "correct": int(values.get(key, 0)) == amount,
        }
        for key, amount in expected.items()
    }
    effect_result = {
        "submitted": effect,
        "expected": QUANTITY_EFFECT_CORRECT,
        "correct": effect == QUANTITY_EFFECT_CORRECT,
    }
    return {
        "fields": fields,
        "effect": effect_result,
        "correct": all(item["correct"] for item in fields.values()) and effect_result["correct"],
    }


def expected_cost_values() -> dict[str, int]:
    results = method_results()
    available = goods_available()
    values = {
        "fifo_ending_inventory": results["FIFO"].ending_inventory,
        "fifo_cogs": results["FIFO"].cost_of_goods_sold,
        "lifo_ending_inventory": results["LIFO"].ending_inventory,
        "lifo_cogs": results["LIFO"].cost_of_goods_sold,
        "average_unit_cost": round(available["cost"] / available["units"]),
        "average_ending_inventory": results["Average cost"].ending_inventory,
        "average_cogs": results["Average cost"].cost_of_goods_sold,
    }
    assert set(values) == {key for key, _label, _expected in COST_FIELDS}
    return values


def evaluate_costing(values: Mapping[str, int]) -> dict[str, object]:
    expected = expected_cost_values()
    fields = {
        key: {
            "submitted": int(values.get(key, 0)),
            "expected": amount,
            "correct": int(values.get(key, 0)) == amount,
        }
        for key, amount in expected.items()
    }
    return {
        "fields": fields,
        "correct": all(item["correct"] for item in fields.values()),
    }


def inventory_metrics(method: str = "FIFO") -> dict[str, float]:
    result = method_results()[method]
    beginning_inventory = BEGINNING_UNITS * BEGINNING_UNIT_COST
    average_inventory = (beginning_inventory + result.ending_inventory) / 2
    turnover = result.cost_of_goods_sold / average_inventory
    return {
        "average_inventory": average_inventory,
        "inventory_turnover": turnover,
        "days_in_inventory": 365 / turnover,
    }


def expected_analysis_values() -> dict[str, int | float]:
    metrics = inventory_metrics("FIFO")
    values: dict[str, int | float] = {
        "average_inventory": round(metrics["average_inventory"]),
        "inventory_turnover": round(metrics["inventory_turnover"], 2),
        "days_in_inventory": round(metrics["days_in_inventory"]),
    }
    assert set(values) == {key for key, _label, _expected in ANALYSIS_FIELDS}
    return values


def evaluate_analysis(
    values: Mapping[str, int | float],
    interpretation: str,
    recommendation: str,
) -> dict[str, object]:
    expected = expected_analysis_values()
    fields = {}
    for key, expected_value in expected.items():
        submitted = float(values.get(key, 0))
        tolerance = 0.01 if key == "inventory_turnover" else 0.5
        fields[key] = {
            "submitted": submitted,
            "expected": expected_value,
            "correct": abs(submitted - float(expected_value)) <= tolerance,
        }
    interpretation_result = {
        "submitted": interpretation,
        "expected": ANALYSIS_INTERPRETATION_CORRECT,
        "correct": interpretation == ANALYSIS_INTERPRETATION_CORRECT,
    }
    recommendation_result = {
        "submitted": recommendation,
        "expected": ANALYSIS_RECOMMENDATION_CORRECT,
        "correct": recommendation == ANALYSIS_RECOMMENDATION_CORRECT,
    }
    return {
        "fields": fields,
        "interpretation": interpretation_result,
        "recommendation": recommendation_result,
        "correct": (
            all(item["correct"] for item in fields.values())
            and interpretation_result["correct"]
            and recommendation_result["correct"]
        ),
    }
