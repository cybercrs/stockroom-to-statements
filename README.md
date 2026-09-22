# Stockroom to Statements

Stockroom to Statements is a Streamlit learning experience for an introductory accounting course. Students follow one fictional retailer's inventory from classification and ownership through physical-count reconciliation, FIFO/LIFO/average-cost assignment, financial-statement effects, inventory turnover, days in inventory, and a management recommendation.

The activity deliberately uses only one beginning-inventory layer and one purchase layer. Student reasoning is expressed through account increases and decreases, ending account balances, and financial-statement effects. Bookkeeping mechanics outside the course are not required.

## Student flow

1. Screen goods by purpose and ownership
2. Reconcile the ending quantity and shrinkage
3. Assign cost with FIFO, LIFO, and weighted average
4. Interpret account balances and financial-statement effects
5. Analyze inventory turnover and days in inventory
6. Complete the case debrief

Progress—including unfinished choices and calculations—is stored anonymously in a validated query parameter so a browser refresh does not erase in-progress work. No login, database, secrets, written response, or student-identifying information is required.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Verify

```bash
python -m unittest discover -s tests -v
python -m py_compile streamlit_app.py stockroom_to_statements/*.py
```
