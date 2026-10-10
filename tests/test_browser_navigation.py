"""Reached-page limits, immutable review, refresh, drafts and independent sessions."""

import unittest
from copy import deepcopy
from streamlit.testing.v1 import AppTest
from browser.navigation import GROUPS, VIEW_KEY, frontier, restore_view, move, advance
from tests.test_browser_flow import BROWSER_APP, button


class BrowserNavigationTests(unittest.TestCase):
    def test_review_preserves_earned_progress_and_current_draft(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        button(app, "Begin the inventory review").click().run()
        items, key, responses = GROUPS[1]
        first = items[0]
        app.radio[0].set_value(first.correct)
        next(b for b in app.button if b.label.startswith("Check")).click().run()
        button(app, "Continue").click().run()
        app.radio[0].set_value(items[1].correct).run()
        token = app.query_params["progress"]
        order = app.radio[0].options
        for _ in range(3):
            button(app, "Back").click().run()
            self.assertFalse(app.radio)
            self.assertFalse(app.number_input)
            self.assertEqual(
                [b.label for b in app.button if not b.disabled], ["Back", "Forward"]
            )
            self.assertEqual(app.query_params["progress"], token)
            button(app, "Forward").click().run()
            self.assertEqual(app.query_params["progress"], token)
            self.assertEqual(app.radio[0].value, items[1].correct)
            self.assertEqual(app.radio[0].options, order)
            self.assertTrue(button(app, "Forward").disabled)
        button(app, "Back").click().run()
        clone = AppTest.from_file(BROWSER_APP, default_timeout=90)
        clone.query_params.update(app.query_params)
        clone.run()
        self.assertFalse(clone.radio)
        self.assertEqual(clone.query_params["progress"], token)
        button(clone, "Forward").click().run()
        self.assertEqual(clone.radio[0].value, items[1].correct)
        future = AppTest.from_file(BROWSER_APP, default_timeout=90)
        future.query_params.update(app.query_params)
        future.query_params["view"] = "999"
        future.run()
        self.assertEqual(future.session_state[VIEW_KEY], 2)
        self.assertTrue(button(future, "Forward").disabled)
        fresh = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        self.assertEqual(fresh.session_state[VIEW_KEY], 0)
        button(app, "Forward").click().run()
        button(app, "Start over").click().run()
        self.assertEqual(app.session_state[VIEW_KEY], 0)
        self.assertFalse(app.session_state[responses])
        self.assertFalse(app.exception)

    def test_navigation_and_advance_reject_locked_future_and_review_mutation(self):
        app = AppTest.from_file(BROWSER_APP, default_timeout=90).run()
        state = deepcopy(dict(app.session_state.filtered_state))
        self.assertFalse(move(state, 1))
        self.assertTrue(advance(state))
        saved = deepcopy(state)
        self.assertFalse(advance(state))
        self.assertEqual(state, saved)
        self.assertTrue(move(state, -1))
        saved = deepcopy(state)
        self.assertFalse(advance(state))
        self.assertEqual(state, saved)
        restore_view(state, "999")
        self.assertEqual(state[VIEW_KEY], frontier(state))
