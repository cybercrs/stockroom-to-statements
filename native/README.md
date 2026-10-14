# Stockroom to Statements — JavaScript app

The final student app is published under `/js/` in the existing repository. It uses local HTML, CSS and JavaScript assets, with no Python, Streamlit, Pyodide, package installation, external service or central storage. The original Python app and the existing stlite site root remain unchanged.

The native implementation preserves the inventory lesson: all ownership decisions, physical-count reconciliation, shrinkage effects, three cost-flow method tabs, statement reasoning, inventory analysis, and the completed debrief. `export.py` captures all 17 original teaching positions in unanswered, incorrect and correct states without changing Python teaching content. Native calculation and randomization tests compare independent Python outcomes, including exact 63-bit shuffle seeds and ties-to-even whole-dollar rounding.

Back reviews earlier reached pages without editing, submitting, revealing hints, resetting or changing scores. Forward stops at the current earned page. The original validated Continue/Finish controls advance. The action model guards these rules independently of the rendered controls. Cost-method tabs, table sorting/expansion and CSV downloads change presentation only.

Original version-2 Python/stlite `progress` links restore after changing the path to `/js/`, retaining their query parameters, drafts, seed, answers, scoring and review position. Ordinary native snapshots use the same version-2 schema and are accepted by the original Python validator. Attempts above the old saved limit of 99 upgrade to native version 3 so practice history remains refreshable; those extended links require this JavaScript app. A separate bounded `draft` query parameter preserves unfinished numeric formatting and invalid numeric text without accepting names or arbitrary text. Invalid or future state is rejected; a future view is clamped to the earned page. Reset creates a fresh anonymous seed and progress URL. Tabs and browser contexts remain independent.

Development and validation use Python and Node only:

```sh
PY=/workspace/.cloud-setup/venvs/main/bin/python
"$PY" native/export.py
node --test native/tests/*.test.mjs
"$PY" -m unittest discover -s tests -v
"$PY" native/build.py
"$PY" native/tests/browser.py
```

Serve `native/dist/` over HTTP/HTTPS. The build creates only `js/` and its SHA-256 manifest. Publication adds this directory to the existing static branch after checking current refs and proving all existing publishing files are unchanged. There are no redirects or provisional titles. See [validation](VALIDATION.md) and `review/` for evidence. Current browsers need ES modules, BigInt, Web Crypto and Compression Streams.
