"""Fictional Chapter 9 case content for Stockroom to Statements."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    id: str
    evidence: str
    title: str
    story: str
    prompt: str
    options: tuple[str, ...]
    correct: str
    explanation: str
    account_effect: str
    statement_effect: str
    hint: str = "Re-read the evidence and focus on the underlying inventory principle."


COMPANY_NAME = "Flyer Cycle Works"
REPORTING_DATE = "December 31"

INCLUDE_OPTIONS = (
    "Include in Flyer Cycle Works inventory",
    "Exclude from Flyer Cycle Works inventory",
)

COUNT_DECISIONS = (
    Decision(
        id="sales_floor",
        evidence="Sales floor tag",
        title="Bicycles ready for customers",
        story=(
            "Flyer Cycle Works owns these bicycles, and they are assembled and ready for sale "
            "in the ordinary course of business."
        ),
        prompt="How should these bicycles be treated?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[0],
        explanation="Owned goods that are ready for sale are merchandise inventory.",
        account_effect="Their cost is included in the ending Inventory account balance.",
        statement_effect="They are included among current assets on the balance sheet.",
        hint="Focus on why the company holds the bicycles, not merely where they are located.",
    ),
    Decision(
        id="repair_stands",
        evidence="Equipment label",
        title="Repair stands used by employees",
        story=(
            "The shop owns four heavy repair stands. Employees use them to service bicycles; "
            "the stands are not held for sale."
        ),
        prompt="How should the repair stands be treated?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[1],
        explanation="The stands are operating equipment, not merchandise held for sale.",
        account_effect="Their cost is not included in the Inventory account balance.",
        statement_effect="They belong with long-lived operating assets rather than current inventory.",
        hint="Ask whether the stands are held for sale or used to operate the business.",
    ),
    Decision(
        id="customer_repairs",
        evidence="Service ticket",
        title="Customer bicycles awaiting tune-ups",
        story=(
            "Six customer-owned bicycles are inside the shop overnight while employees complete "
            "scheduled repairs."
        ),
        prompt="How should the customer bicycles be treated?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[1],
        explanation="Physical possession does not create ownership. The customers still own the bicycles.",
        account_effect="No amount is added to Flyer Cycle Works' Inventory account.",
        statement_effect="The customer property is not an asset of Flyer Cycle Works.",
        hint="Separate physical possession from ownership.",
    ),
    Decision(
        id="consigned_display",
        evidence="Consignment agreement",
        title="Six demonstration bicycles in the physical count",
        story=(
            "A manufacturer placed six demonstration bicycles in the store. Flyer Cycle Works "
            "earns a fee if they sell, but the manufacturer retains ownership. The six bicycles "
            "were included in the warehouse count of 28 units."
        ),
        prompt="How should the six demonstration bicycles be treated?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[1],
        explanation="Goods held on consignment remain inventory of the owner, not the consignee.",
        account_effect="Subtract the six units from the physical count used for Flyer Cycle Works' Inventory balance.",
        statement_effect="Excluding them prevents current assets from being overstated.",
        hint="Under a consignment agreement, identify who retains ownership until a sale occurs.",
    ),
    Decision(
        id="inbound_shipping_point",
        evidence="Inbound shipping document",
        title="Ten purchased bicycles are in transit",
        story=(
            "The supplier transferred ten bicycles to the carrier on December 29. The terms are "
            "FOB shipping point, and the shipment will arrive in January."
        ),
        prompt="How should the ten bicycles be treated on December 31?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[0],
        explanation="With FOB shipping point, ownership passes to the buyer when the carrier accepts the goods.",
        account_effect="Add the ten units to the quantity used for the ending Inventory balance.",
        statement_effect="Including the owned goods prevents current assets from being understated.",
        hint="Use the shipping term to identify when ownership passes from seller to buyer.",
    ),
    Decision(
        id="outbound_destination",
        evidence="Outbound shipping document",
        title="Eight sold bicycles are traveling to a customer",
        story=(
            "Flyer Cycle Works shipped eight bicycles on December 30 using FOB destination. "
            "The customer will receive them in January."
        ),
        prompt="How should the eight bicycles be treated on December 31?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[0],
        explanation="With FOB destination, the seller retains ownership until the goods reach the buyer.",
        account_effect="Add the eight units to the quantity used for the ending Inventory balance.",
        statement_effect="The company still reports these owned goods as current assets at year-end.",
        hint="For FOB destination, decide whether ownership has passed before the customer receives the goods.",
    ),
    Decision(
        id="inbound_destination",
        evidence="Second inbound shipping document",
        title="Four more purchased bicycles are in transit",
        story=(
            "A different supplier shipped four bicycles on December 30 using FOB destination. "
            "Flyer Cycle Works will receive them in January."
        ),
        prompt="How should the four bicycles be treated on December 31?",
        options=INCLUDE_OPTIONS,
        correct=INCLUDE_OPTIONS[1],
        explanation="The seller retains ownership until an FOB-destination shipment reaches the buyer.",
        account_effect="Do not add the four units to Flyer Cycle Works' ending Inventory quantity.",
        statement_effect="Excluding goods not yet owned prevents current assets from being overstated.",
        hint="For an inbound FOB-destination shipment, decide whether the buyer owns the goods before arrival.",
    ),
)


PHYSICAL_COUNT = 28
CONSIGNED_UNITS = 6
INBOUND_SHIPPING_POINT_UNITS = 10
OUTBOUND_DESTINATION_UNITS = 8
INBOUND_DESTINATION_UNITS = 4
RECORDS_EXPECTED_UNITS = 44

QUANTITY_FIELDS = (
    ("ending_units", "Correct ending inventory quantity", 40),
    ("shrinkage_units", "Inventory shrinkage", 4),
)

QUANTITY_EFFECT_OPTIONS = (
    "Inventory decreases; cost of goods sold increases; total assets and net income decrease",
    "Inventory increases; cost of goods sold decreases; total assets and net income increase",
    "Inventory and cost of goods sold both increase; total assets do not change",
)
QUANTITY_EFFECT_CORRECT = QUANTITY_EFFECT_OPTIONS[0]


BEGINNING_UNITS = 80
BEGINNING_UNIT_COST = 120
PURCHASE_UNITS = 120
PURCHASE_UNIT_COST = 150
SALES_REVENUE = 34_000

COST_FIELDS = (
    ("fifo_ending_inventory", "FIFO ending Inventory", 6_000),
    ("fifo_cogs", "FIFO cost of goods sold", 21_600),
    ("lifo_ending_inventory", "LIFO ending Inventory", 4_800),
    ("lifo_cogs", "LIFO cost of goods sold", 22_800),
    ("average_unit_cost", "Weighted-average unit cost", 138),
    ("average_ending_inventory", "Average-cost ending Inventory", 5_520),
    ("average_cogs", "Average-cost cost of goods sold", 22_080),
)


REPORTING_DECISIONS = (
    Decision(
        id="highest_inventory",
        evidence="Method comparison",
        title="Explain where the newest costs remain",
        story="Unit costs rose from $120 in beginning inventory to $150 in the purchase layer.",
        prompt="Why does FIFO report a higher ending Inventory balance than LIFO when unit costs are rising?",
        options=(
            "FIFO leaves the newer, higher-cost units in ending inventory",
            "FIFO assumes the company owns more physical units at year-end",
            "FIFO creates a larger total cost of goods available for sale",
        ),
        correct="FIFO leaves the newer, higher-cost units in ending inventory",
        explanation="FIFO assigns the older costs to sold units first, leaving the newer, higher costs in ending inventory.",
        account_effect="Compared with LIFO, FIFO reports Inventory $1,200 higher.",
        statement_effect="Compared with LIFO, total assets are $1,200 higher before income tax effects.",
        hint="Track which cost layer remains after the older units are assigned to sold units under FIFO.",
    ),
    Decision(
        id="fifo_income_effect",
        evidence="Income statement comparison",
        title="Trace the inverse cost relationship",
        story=(
            "The cost assigned to ending inventory is not assigned to cost of goods sold. "
            "The total cost available remains $27,600 under every method."
        ),
        prompt="Why does FIFO report lower Cost of Goods Sold and higher gross profit than LIFO in this rising-cost case?",
        options=(
            "More available cost remains in ending inventory, leaving less cost assigned to sold units",
            "FIFO records more sales revenue than LIFO",
            "FIFO uses fewer physical units when calculating Cost of Goods Sold",
        ),
        correct="More available cost remains in ending inventory, leaving less cost assigned to sold units",
        explanation="Because the total cost available is fixed, assigning more cost to ending inventory leaves less cost in Cost of Goods Sold and raises gross profit.",
        account_effect="Cost of Goods Sold is $1,200 lower under FIFO than under LIFO.",
        statement_effect="Gross profit and net income are $1,200 higher before income tax effects.",
        hint="The total cost available does not change. Focus on the inverse relationship between ending Inventory and Cost of Goods Sold.",
    ),
    Decision(
        id="average_position",
        evidence="Method comparison",
        title="Interpret the weighted average",
        story="Average cost blends the $120 and $150 unit costs into one $138 unit cost.",
        prompt="Why do weighted-average Inventory and Cost of Goods Sold amounts fall between the FIFO and LIFO amounts?",
        options=(
            "Weighted average blends the costs of both layers before assigning cost to units",
            "Weighted average always selects the midpoint of the FIFO and LIFO dollar amounts",
            "Weighted average changes the number of units available for sale",
        ),
        correct="Weighted average blends the costs of both layers before assigning cost to units",
        explanation="Blending the lower and higher unit costs creates a single unit cost between them, so the assigned amounts also fall between FIFO and LIFO.",
        account_effect="The ending Inventory and Cost of Goods Sold balances fall between FIFO and LIFO.",
        statement_effect="Gross profit also falls between the FIFO and LIFO results.",
        hint="Consider what happens when the two unit costs are blended rather than kept in separate layers.",
    ),
    Decision(
        id="specific_identification",
        evidence="Serial-number records",
        title="Management can choose which identified units are sold",
        story=(
            "Assume every bicycle can be traced to its original cost. Management wants the highest "
            "current-period income while selling the same number of units."
        ),
        prompt="Why can management influence current-period income when specific identification is used?",
        options=(
            "The actual costs of the particular units selected as sold determine Cost of Goods Sold",
            "Specific identification allows management to change the sales price after the sale",
            "Specific identification assigns the same average cost to every unit",
        ),
        correct="The actual costs of the particular units selected as sold determine Cost of Goods Sold",
        explanation="Assigning lower identified costs to sold units lowers cost of goods sold and raises current-period income.",
        account_effect="Lower-cost units leave Inventory; more high-cost units remain in the ending balance.",
        statement_effect="Cost of goods sold is lower, so gross profit and net income are higher.",
        hint="Under specific identification, focus on how the actual cost of each selected sold unit affects Cost of Goods Sold.",
    ),
    Decision(
        id="presentation",
        evidence="Draft financial statements",
        title="Explain where inventory costs belong",
        story="The controller is reviewing the year-end balance sheet and income statement.",
        prompt="Why is ending Inventory reported as a current asset while Cost of Goods Sold appears on the income statement?",
        options=(
            "Ending inventory provides a future benefit; Cost of Goods Sold is a cost of current-period operations",
            "Inventory is always more liquid than cash, while Cost of Goods Sold is not measurable",
            "The two amounts are placed on different statements only because they use different cost methods",
        ),
        correct="Ending inventory provides a future benefit; Cost of Goods Sold is a cost of current-period operations",
        explanation="Ending inventory remains available for future sale and is reported as a current asset. Cost of Goods Sold is the cost of merchandise sold as part of current-period operations and reduces net sales in determining gross profit.",
        account_effect="The ending Inventory balance remains on the balance sheet; sold-unit cost is in Cost of Goods Sold.",
        statement_effect="The balance sheet reports Inventory, and the income statement reports Cost of Goods Sold and gross profit.",
        hint="Ask which costs remain available for future sale and which were consumed in current-period operations.",
    ),
)


ANALYSIS_FIELDS = (
    ("average_inventory", "Average inventory", 7_800),
    ("inventory_turnover", "Inventory turnover", 2.77),
    ("days_in_inventory", "Days in inventory", 132),
)

TURNOVER_BENCHMARK = 4.50
DAYS_BENCHMARK = 81

ANALYSIS_INTERPRETATION_OPTIONS = (
    "Inventory is moving more slowly than the industry average, with funds tied up longer",
    "Inventory is moving faster than the industry average, with fewer funds tied up",
    "The company cannot be compared with the industry because one measure uses dollars and the other uses days",
)
ANALYSIS_INTERPRETATION_CORRECT = ANALYSIS_INTERPRETATION_OPTIONS[0]

ANALYSIS_RECOMMENDATION_OPTIONS = (
    "Identify slow-moving models, adjust future purchases, and use targeted promotions",
    "Increase every model's purchase quantity without reviewing demand",
    "Ignore the result because inventory turnover does not affect operating decisions",
)
ANALYSIS_RECOMMENDATION_CORRECT = ANALYSIS_RECOMMENDATION_OPTIONS[0]
