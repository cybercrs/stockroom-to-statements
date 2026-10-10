# stockroom-to-statements browser validation

Local validation completed on 2026-10-10 in the saved Accounting Teaching Apps environment.

| Check | Result | Evidence |
| --- | --- | --- |
| Existing unit/AppTest suite and browser regressions | Passed: 26 tests | [unit.log](review/unit.log) |
| Actual Chromium/stlite/Wasm walkthrough | Passed: 7 scenario groups | [browser-results.json](review/browser-results.json), [browser.log](review/browser.log) |
| Ruff 0.14.0: browser code and new tests | Passed | [browser-lint.log](review/browser-lint.log) |
| Python compilation; JavaScript loader syntax; whitespace | Passed | [compile.log](review/compile.log), [javascript.log](review/javascript.log), [whitespace.log](review/whitespace.log) |
| Pinned archive and local asset hashes; repeat build | Passed; byte identical | [build-checks.json](review/build-checks.json), [file hashes](review/bundle-files-sha256.json) |
| Server files and teaching package compared with origin/main | Byte unchanged | [build-checks.json](review/build-checks.json) |
| Hosted HTTPS walkthrough; real devices/browser matrix; classroom concurrency | Not run | Pages needs activation; known cloud proxy restriction respected |

Actual runtime: Streamlit 1.57.0, Pyodide 0.29.3, Python 3.13.2; stlite 1.8.1 comes from the locked build. Tests served the bundle under `/lesson/` with an intentionally closed external proxy. Zero external requests, zero console errors, and zero page execution errors were recorded. This is a local functional result, not a classroom-capacity measurement.

The walkthrough covers a complete lesson, deliberate wrong answers, original correction/reveal behavior, repeated read-only review, future-view rejection, refresh/bookmarks, reset, independent tabs and browser contexts, keyboard focus/Enter, 44-pixel arrow targets, and a 390-pixel viewport. A final run verifies native sidebar access for reset or facilitator controls on that narrow viewport. Activity input/submission/reveal/reset controls are unavailable in review; dataframe inspection controls may remain because they do not change progress.

Original validated URL snapshots preserve current answers, calculation and choice drafts, attempt history, scoring flags, shuffle seed, and earned position. Separate `view` is bounded by that earned position. Earlier views render a defensive state copy with no progress controls.

Full-repository Ruff also passed.

Screenshots: [briefing](review/briefing.png), [completion](review/completed.png), [narrow view](review/narrow.png), and the relevant review/sidebar images in [review/](review/). These are emulated Chromium viewports, not physical-device tests.

Compatibility fixes are isolated to the browser driver and UI: restore the sidebar opener hidden by original server CSS; retain original draft selections; use the supported `st.iframe` scroll reset for Build It. Runtime assets and server dependencies remain pinned separately. Early development failures involved harness timing, hidden radio locators, and collapsed sidebar access; final evidence above is the completed run.

Static distribution: 243 files, 59,063,528 bytes before publishing provenance and CI. The independent source and static branches are in this repository. GitHub metadata reported no existing Pages site. Main is preserved and no merge is performed. Remote CI is recorded by GitHub for the exact source/static commits and is reported separately after push.

The cloud proxy's known Pages-host restriction is respected. No hosted public URL is claimed as verified. Enable the unused static branch through the exact Settings → Pages steps in [README.md](README.md), then perform hosted verification on classroom devices.
