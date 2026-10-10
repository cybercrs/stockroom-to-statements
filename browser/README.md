# stockroom-to-statements browser version

This browser version uses the accepted Dock to Dollar source commit `8a0f25a2bff6f9f1eacbc8ab132ababc94974c87` as its build reference. It runs entirely in the browser, with a dedicated worker per tab and no Python server or central grade store.

The original `streamlit_app.py`, teaching package, requirements, `.streamlit/`, existing tests, and original server CI remain unchanged. A separate entrypoint extracts only the original renderer declarations, then adds browser navigation. The build rejects an unexpected server driver. All teaching modules retain their package paths.

## Build and verify

```bash
PY=/workspace/.cloud-setup/venvs/main/bin/python
"$PY" -m browser.build
"$PY" -m unittest discover -s tests -v
"$PY" -m browser.test_browser
```

A cached build can use `--runtime-archive /tmp/assigned-stlite-cache/stlite-browser-1.8.1.tgz --asset-cache /tmp/assigned-stlite-cache`. Archive integrity and every asset hash are always checked. Serve `browser/dist/` using an ordinary static HTTP server; `file://` is unsupported. Root and repository subdirectory hosting use relative URLs.

The runtime is stlite 1.8.1, its bundled patched Streamlit 1.57.0, Pyodide 0.29.3, and Python 3.13.2. Do not install the server's Streamlit requirement into stlite. JavaScript, fonts, WebAssembly, standard library, and dependency wheels are packaged locally using the pilot's committed runtime lock. No external asset request is required at runtime.

## Navigation

Use the compact boxed Back and Forward arrows at the upper right. They retain native accessible names, help text, keyboard focus, Enter activation, and 44-pixel touch targets.

Earlier views expose saved content without answer inputs, submissions, revisions, scoring, hints/reveals, or activity reset. The review renderer reads a defensive copy of state, so rendering cannot mutate earned progress. Forward only visits already reached pages and stops on the actual current page. Use that page's original validation controls to advance.

Activity controls are the supported navigation interface. Browser toolbar history is not an activity navigation contract.

## Saved student progress

The original validated `progress` URL schema still records the actual current position, answers, drafts, attempt history, first-pass flags, and stable shuffle seed. A separate range-checked `view` parameter records the page being reviewed. Refresh and copied bookmarks restore both; invalid or future views fall back to the earned position. Invalid snapshots begin a new activity. Drafts survive navigation and refresh. Start over is disabled while reviewing and replaces the current saved activity with a fresh one; an older copied bookmark can still resume its own snapshot.

Choice pages follow each case's original fixed question sequence. Numeric gates remain attached to their original stage and reveal interpretation questions only after the original calculation validation succeeds. Current-page revision behavior and feedback remain those of the teaching app.

## Separate publication

The source branch is `rollout/stlite-browser-navigation`; the static publishing branch is `stlite-browser`. Both are in this same repository. Neither is merged into main. The static branch has an independent root and contains the tested bundle, provenance, and static integrity CI.

GitHub metadata reported `has_pages: false` before rollout. Current tools cannot change Pages settings. After verifying there is still no site to replace, choose **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: stlite-browser → Folder: / (root) → Save**. Wait for the Pages build and deployment to succeed, then verify the URL GitHub reports on actual classroom devices. Do not redirect the Streamlit deployment to either branch.

The saved cloud proxy previously denied the `cybercrs.github.io` hostname. Hosted browser testing is not performed through an alternate route. No public URL is claimed as verified here.

The actual Chromium walkthrough is functional validation only. It does not establish capacity for 40–45 or 80–135 simultaneous learners. Initial runtime download and browser memory still need a trial on classroom devices and networks.
