from pathlib import Path
import tempfile
from browser.build import app_files
import re
import unittest

from streamlit.testing.v1 import AppTest

from stockroom_to_statements.case_data import (
    ANALYSIS_INTERPRETATION_CORRECT,
    ANALYSIS_RECOMMENDATION_CORRECT,
    COUNT_DECISIONS,
    QUANTITY_EFFECT_CORRECT,
    QUANTITY_EFFECT_OPTIONS,
    REPORTING_DECISIONS,
)
from stockroom_to_statements.engine import (
    expected_analysis_values,
    expected_cost_values,
    expected_quantity_values,
)
from stockroom_to_statements.progress import SNAPSHOT_PARAM, decode_snapshot


BROWSER_TEMP = tempfile.TemporaryDirectory()
BROWSER_ROOT = Path(BROWSER_TEMP.name)
for name, content in app_files().items():
    target = BROWSER_ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
BROWSER_APP = str(BROWSER_ROOT / "browser/app.py")


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


class PerfectInventoryFlowTests(unittest.TestCase):
    def test_start_over_clears_saved_draft_and_returns_to_brief(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        button(app, "Begin the inventory review").click().run()
        item = COUNT_DECISIONS[0]
        app.radio(key=f"widget_count_{item.id}").set_value(item.correct).run()

        button(app, "Start over").click().run()

        self.assertEqual(app.session_state.sts_stage, 0)
        self.assertTrue(
            any(item.label == "Begin the inventory review" for item in app.button)
        )
        saved_value = app.query_params[SNAPSHOT_PARAM]
        saved = decode_snapshot(
            saved_value[0] if isinstance(saved_value, list) else saved_value
        )
        self.assertEqual(saved["sts_stage"], 0)
        self.assertEqual(saved["sts_drafts"]["count"], {})

    def test_draft_restores_and_wrong_answer_revises_in_place(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        button(app, "Begin the inventory review").click().run()
        item = COUNT_DECISIONS[0]
        wrong = next(option for option in item.options if option != item.correct)

        self.assertNotEqual(
            app.radio(key=f"widget_count_{item.id}").options, list(item.options)
        )
        app.radio(key=f"widget_count_{item.id}").set_value(wrong).run()
        saved_value = app.query_params[SNAPSHOT_PARAM]
        saved = decode_snapshot(
            saved_value[0] if isinstance(saved_value, list) else saved_value
        )
        self.assertEqual(saved["sts_drafts"]["count"][item.id], wrong)

        button(app, "Check this item").click().run()
        feedback = "\n".join(
            str(element.value)
            for collection in (app.warning, app.info, app.caption, app.markdown)
            for element in collection
        )
        self.assertNotIn("Best response", feedback)
        self.assertNotIn(item.correct, feedback)
        self.assertNotIn(item.explanation, feedback)
        self.assertTrue(
            any(item.label == "Check revised response" for item in app.button)
        )
        app.radio(key=f"widget_count_{item.id}").set_value(item.correct)
        button(app, "Check revised response").click().run()

        self.assertEqual(app.session_state.sts_count_responses[item.id], item.correct)
        self.assertTrue(any(item.label == "Continue" for item in app.button))

    def test_incorrect_calculations_receive_hints_without_expected_answers(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        button(app, "Begin the inventory review").click().run()
        for item in COUNT_DECISIONS:
            app.radio(key=f"widget_count_{item.id}").set_value(item.correct)
            button(app, "Check this item").click().run()
            button(app, "Continue").click().run()

        for key in expected_quantity_values():
            app.number_input(key=f"widget_quantity_{key}").set_value(1)
        wrong_effect = next(
            option
            for option in QUANTITY_EFFECT_OPTIONS
            if option != QUANTITY_EFFECT_CORRECT
        )
        app.radio(key="widget_quantity_effect").set_value(wrong_effect)
        button(app, "Check the reconciliation").click().run()
        quantity_feedback = "\n".join(str(item.value) for item in app.markdown)
        self.assertNotIn("Expected", quantity_feedback)
        self.assertIn("Compare the accounting system", quantity_feedback)
        self.assertIn("44 units", quantity_feedback)

    def test_incorrect_costing_receives_hints_without_expected_answers(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        button(app, "Begin the inventory review").click().run()
        for item in COUNT_DECISIONS:
            app.radio(key=f"widget_count_{item.id}").set_value(item.correct)
            button(app, "Check this item").click().run()
            button(app, "Continue").click().run()

        for key, value in expected_quantity_values().items():
            app.number_input(key=f"widget_quantity_{key}").set_value(value)
        app.radio(key="widget_quantity_effect").set_value(QUANTITY_EFFECT_CORRECT)
        button(app, "Check the reconciliation").click().run()
        button(app, "Continue to cost assignment").click().run()

        button(app, "Check all three methods").click().run()
        cost_feedback = "\n".join(str(item.value) for item in app.markdown)
        self.assertNotIn("Expected", cost_feedback)
        self.assertIn("Under FIFO, identify which layer", cost_feedback)

    def test_complete_case_reaches_debrief_without_excluded_mechanics(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        self.assertFalse(app.exception)
        button(app, "Begin the inventory review").click().run()

        for item in COUNT_DECISIONS:
            app.radio(key=f"widget_count_{item.id}").set_value(item.correct)
            button(app, "Check this item").click().run()
            button(app, "Continue").click().run()

        quantity_copy = "\n".join(item.value for item in app.markdown)
        self.assertIn("already excluded from the warehouse count", quantity_copy)
        self.assertIn("accounting system shows 44 units on hand", quantity_copy)
        self.assertNotIn("shown for completeness", quantity_copy)

        for key, value in expected_quantity_values().items():
            app.number_input(key=f"widget_quantity_{key}").set_value(value)
        app.radio(key="widget_quantity_effect").set_value(
            "Inventory decreases; cost of goods sold increases; total assets and net income decrease"
        )
        button(app, "Check the reconciliation").click().run()
        button(app, "Continue to cost assignment").click().run()
        self.assertNotIn(
            "Cost relationship", "\n".join(item.value for item in app.markdown)
        )

        for key, value in expected_cost_values().items():
            app.number_input(key=f"widget_cost_{key}").set_value(value)
        button(app, "Check all three methods").click().run()
        button(app, "Continue to financial-statement effects").click().run()

        for item in REPORTING_DECISIONS:
            app.radio(key=f"widget_reporting_{item.id}").set_value(item.correct)
            button(app, "Check the reasoning").click().run()
            button(app, "Continue").click().run()

        analysis_copy = "\n".join(item.value for item in app.markdown).lower()
        self.assertIn("industry average turnover", analysis_copy)
        self.assertIn("industry average days in inventory", analysis_copy)
        self.assertIn("round inventory turnover to two decimal places", analysis_copy)
        self.assertNotIn("formulas", analysis_copy)
        self.assertIn(
            "industry averages", app.radio(key="widget_analysis_interpretation").label
        )

        for key, value in expected_analysis_values().items():
            app.number_input(key=f"widget_analysis_{key}").set_value(value)
        app.radio(key="widget_analysis_interpretation").set_value(
            ANALYSIS_INTERPRETATION_CORRECT
        )
        app.radio(key="widget_analysis_recommendation").set_value(
            ANALYSIS_RECOMMENDATION_CORRECT
        )
        button(app, "Check the inventory analysis").click().run()
        button(app, "Finish the case").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any("Case complete" in item.value for item in app.success))
        self.assertIn(
            "final mastery: complete",
            "\n".join(item.value for item in app.caption).lower(),
        )

        rendered = "\n".join(item.value for item in app.markdown).lower()
        for banned in (
            r"\bdebits?\b",
            r"\bcredits?\b",
            r"\bjournal entries?\b",
            r"\bledger\b",
            r"\bposting\b",
            r"\bjust-in-time\b",
            r"\bjit\b",
        ):
            self.assertIsNone(re.search(banned, rendered), banned)

        saved_value = app.query_params[SNAPSHOT_PARAM]
        saved = decode_snapshot(
            saved_value[0] if isinstance(saved_value, list) else saved_value
        )
        self.assertIsNotNone(saved)
        self.assertEqual(saved["sts_stage"], 6)
        self.assertEqual(
            len(saved["sts_reporting_responses"]), len(REPORTING_DECISIONS)
        )


if __name__ == "__main__":
    unittest.main()
