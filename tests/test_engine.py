import unittest

from stockroom_to_statements.case_data import (
    ANALYSIS_INTERPRETATION_CORRECT,
    ANALYSIS_RECOMMENDATION_CORRECT,
    COUNT_DECISIONS,
    REPORTING_DECISIONS,
)
from stockroom_to_statements.engine import (
    evaluate_analysis,
    evaluate_costing,
    evaluate_decision,
    evaluate_quantity,
    expected_analysis_values,
    expected_cost_values,
    expected_quantity_values,
    goods_available,
    inventory_metrics,
    method_results,
    quantity_reconciliation,
)


class InventoryEngineTests(unittest.TestCase):
    def test_quantity_reconciliation_and_shrinkage(self):
        values = quantity_reconciliation()
        self.assertEqual(values["ending_units"], 40)
        self.assertEqual(values["shrinkage_units"], 4)
        self.assertEqual(values["exclude_inbound_destination"], 4)

    def test_two_layers_reconcile(self):
        available = goods_available()
        self.assertEqual(available["units"], 200)
        self.assertEqual(available["cost"], 27_600)

        results = method_results()
        self.assertEqual(results["FIFO"].ending_inventory, 6_000)
        self.assertEqual(results["FIFO"].cost_of_goods_sold, 21_600)
        self.assertEqual(results["LIFO"].ending_inventory, 4_800)
        self.assertEqual(results["LIFO"].cost_of_goods_sold, 22_800)
        self.assertEqual(results["Average cost"].ending_inventory, 5_520)
        self.assertEqual(results["Average cost"].cost_of_goods_sold, 22_080)
        for result in results.values():
            self.assertEqual(result.ending_inventory + result.cost_of_goods_sold, 27_600)

    def test_rising_cost_statement_order(self):
        results = method_results()
        self.assertGreater(results["FIFO"].ending_inventory, results["Average cost"].ending_inventory)
        self.assertGreater(results["Average cost"].ending_inventory, results["LIFO"].ending_inventory)
        self.assertLess(results["FIFO"].cost_of_goods_sold, results["Average cost"].cost_of_goods_sold)
        self.assertLess(results["Average cost"].cost_of_goods_sold, results["LIFO"].cost_of_goods_sold)

    def test_inventory_analysis(self):
        metrics = inventory_metrics("FIFO")
        self.assertEqual(metrics["average_inventory"], 7_800)
        self.assertAlmostEqual(metrics["inventory_turnover"], 2.7692307, places=6)
        self.assertAlmostEqual(metrics["days_in_inventory"], 131.8055, places=3)

    def test_combined_evaluators(self):
        quantity = expected_quantity_values()
        quantity_result = evaluate_quantity(
            quantity,
            "Inventory decreases; cost of goods sold increases; total assets and net income decrease",
        )
        self.assertTrue(quantity_result["correct"])
        self.assertTrue(evaluate_costing(expected_cost_values())["correct"])

        analysis = expected_analysis_values()
        analysis_result = evaluate_analysis(
            analysis,
            ANALYSIS_INTERPRETATION_CORRECT,
            ANALYSIS_RECOMMENDATION_CORRECT,
        )
        self.assertTrue(analysis_result["correct"])

    def test_decision_evaluation(self):
        for item in (*COUNT_DECISIONS, *REPORTING_DECISIONS):
            result = evaluate_decision(item.id, item.correct)
            self.assertTrue(result["correct"], item.id)
            self.assertTrue(result["account_effect"])
            self.assertTrue(result["statement_effect"])

    def test_reporting_questions_require_conceptual_explanations(self):
        self.assertTrue(all("why" in item.prompt.lower() for item in REPORTING_DECISIONS))
        self.assertTrue(all(item.hint for item in REPORTING_DECISIONS))
        self.assertTrue(all(item.correct not in item.hint for item in REPORTING_DECISIONS))


if __name__ == "__main__":
    unittest.main()
