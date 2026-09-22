import base64
import json
import unittest
import zlib

from stockroom_to_statements.case_data import (
    ANALYSIS_INTERPRETATION_CORRECT,
    ANALYSIS_RECOMMENDATION_CORRECT,
    COUNT_DECISIONS,
    REPORTING_DECISIONS,
)
from stockroom_to_statements.engine import (
    expected_analysis_values,
    expected_cost_values,
    expected_quantity_values,
)
from stockroom_to_statements.progress import (
    SNAPSHOT_PARAM,
    activity_defaults,
    decode_snapshot,
    encode_state,
    record_attempt,
    reset_saved_progress,
    restore_session_state,
    score_summary,
    snapshot_from_state,
)


def encode_raw(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(zlib.compress(raw)).decode("ascii").rstrip("=")


def completed_state():
    state = activity_defaults()
    state["sts_stage"] = 6
    state["sts_count_index"] = len(COUNT_DECISIONS) - 1
    state["sts_count_responses"] = {item.id: item.correct for item in COUNT_DECISIONS}
    state["sts_quantity_values"] = expected_quantity_values()
    state["sts_quantity_effect"] = (
        "Inventory decreases; cost of goods sold increases; total assets and net income decrease"
    )
    state["sts_quantity_submitted"] = True
    state["sts_cost_values"] = expected_cost_values()
    state["sts_cost_submitted"] = True
    state["sts_reporting_index"] = len(REPORTING_DECISIONS) - 1
    state["sts_reporting_responses"] = {item.id: item.correct for item in REPORTING_DECISIONS}
    state["sts_analysis_values"] = expected_analysis_values()
    state["sts_analysis_interpretation"] = ANALYSIS_INTERPRETATION_CORRECT
    state["sts_analysis_recommendation"] = ANALYSIS_RECOMMENDATION_CORRECT
    state["sts_analysis_submitted"] = True
    return state


class ProgressSnapshotTests(unittest.TestCase):
    def test_completed_round_trip(self):
        token = encode_state(completed_state())
        restored = decode_snapshot(token)
        self.assertIsNotNone(restored)
        self.assertEqual(restored["sts_stage"], 6)
        self.assertEqual(restored["sts_cost_values"]["fifo_cogs"], 21_600)
        self.assertNotIn("name", token.lower())
        self.assertNotIn("email", token.lower())

    def test_current_incorrect_answer_can_be_restored(self):
        state = activity_defaults()
        state["sts_stage"] = 1
        item = COUNT_DECISIONS[0]
        state["sts_count_responses"] = {item.id: item.options[-1]}
        record_attempt(state, f"count:{item.id}", False)
        restored = decode_snapshot(encode_state(state))
        self.assertIsNotNone(restored)
        self.assertFalse(restored["sts_first_pass"][f"count:{item.id}"])

    def test_unsubmitted_calculation_draft_survives_refresh(self):
        state = activity_defaults()
        state["sts_stage"] = 2
        state["sts_count_index"] = len(COUNT_DECISIONS) - 1
        state["sts_count_responses"] = {item.id: item.correct for item in COUNT_DECISIONS}
        state["sts_drafts"]["quantity"] = {
            "ending_units": 40,
            "effect": "Inventory decreases; cost of goods sold increases; total assets and net income decrease",
        }

        restored = decode_snapshot(encode_state(state))

        self.assertIsNotNone(restored)
        self.assertEqual(restored["sts_drafts"]["quantity"]["ending_units"], 40)
        self.assertIn("effect", restored["sts_drafts"]["quantity"])

    def test_skipped_stage_is_rejected(self):
        state = activity_defaults()
        state["sts_stage"] = 3
        self.assertIsNone(decode_snapshot(encode_state(state)))

    def test_tampered_completed_costing_is_rejected(self):
        state = completed_state()
        state["sts_cost_values"]["fifo_cogs"] = 1
        self.assertIsNone(decode_snapshot(encode_state(state)))

    def test_malformed_oversized_and_unknown_payloads_are_rejected(self):
        self.assertIsNone(decode_snapshot("not-a-valid-token"))
        self.assertIsNone(decode_snapshot("x" * 16_001))

        token = encode_state(completed_state())
        self.assertIsNotNone(decode_snapshot(token))
        raw = snapshot_from_state(activity_defaults())
        raw["unexpected"] = True
        self.assertIsNone(decode_snapshot(encode_raw(raw)))

    def test_restore_reset_and_score(self):
        destination = {}
        self.assertTrue(restore_session_state(destination, encode_state(completed_state())))
        self.assertEqual(destination["sts_stage"], 6)

        query = {}
        reset_saved_progress(destination, query)
        self.assertEqual(destination["sts_stage"], 0)
        self.assertIn(SNAPSHOT_PARAM, query)
        self.assertIsNotNone(decode_snapshot(query[SNAPSHOT_PARAM]))

        state = activity_defaults()
        record_attempt(state, "count:sales_floor", False)
        record_attempt(state, "count:sales_floor", True)
        score = score_summary(state)
        self.assertEqual(score["attempted"], 1)
        self.assertEqual(score["correct"], 0)
        self.assertEqual(score["revisions"], 1)


if __name__ == "__main__":
    unittest.main()
