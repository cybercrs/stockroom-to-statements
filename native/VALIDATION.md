# Native Stockroom validation

October 14, 2026. The isolated `native/javascript` source branch is based on `eb99706710332f5b4d3eefcffbe522af931101fc`. The final app is added only at `/js/` on the existing `stlite-browser` branch. Main, original Python/Streamlit files, server deployment files and the existing published stlite root remain unchanged. No Pages setting changes or redirects are required.

| Check | Result | Evidence |
| --- | --- | --- |
| Existing unit/AppTest suite | 26 passed | Existing suite and source CI |
| Native calculation, codec, shuffle, action and branding tests | 7 groups passed | [Node log](review/node.log), [Python oracles](tests/python-oracles.json) |
| Packaged Chromium full lesson, wrong answers, revisions, immutable review, bookmarks, reset, independent sessions and keyboard | 9 scenario groups passed | [Browser results](review/browser-results.json), [Browser log](review/browser.log) |
| All 17 original positions and 51 teaching variants | Preserved; provisional branding absent | Generated content and export/CI parity |
| Old version-2 links and exact 63-bit seed with an unfinished costing draft | Restored, future view clamped | Browser fixtures and Node parity |
| Numeric units/ranges, unfinished and invalid draft refresh, unchanged numeric rechecks | Passed | Actual browser and action tests |
| Original tables, native table expansion and CSV | Passed without progress mutation | Downloaded CSV evidence |
| Desktop and 390-pixel pages, including all three numeric forms; 44-pixel arrow targets and visible keyboard focus | Passed | Screenshots in `review/` |
| Ruff, JavaScript syntax, deterministic export, build hashes and whitespace | Passed | Local checks and source CI |
| Hosted browser, physical-device matrix and classroom concurrency | Not run | Known cloud proxy denial respected |

The full walkthrough finishes with the original Python-validated score of **14/27 first-pass correct and 13 revisions** after deliberate wrong work. This includes all original 27 checkpoints. No receivables-specific curriculum changes are applied. Wrong inventory/cost/analysis inputs retain original hints rather than exposing answers. Field-level feedback uses actual submitted values and each field's original correct/incorrect explanation. The FIFO/LIFO/average-cost tabs use accessible native tab controls; tab changes and table operations do not alter progress.

The seven native runtime files total 153,815 bytes. Browser results record five cache-disabled cold initializations in fresh Chromium contexts on local loopback. These measurements do not establish hosted speed, school-network behavior, physical-device performance or classroom capacity. Zero external requests, console errors and page execution errors were recorded.

GitHub's exact source/static refs, CI and Pages deployment are verified after publication. Hosted HTTP/UI checks are unavailable because the cloud proxy previously denied the Pages hostname with tunnel 403; no alternative route is used.
