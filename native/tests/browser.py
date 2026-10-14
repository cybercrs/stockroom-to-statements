"""Run the complete packaged native lesson with all external network traffic blocked."""

from __future__ import annotations
import json
import re
import statistics
import sys
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from browser.scenario import START, PLAN, POSITIONS, decode_snapshot, score_summary  # noqa: E402
from stockroom_to_statements import progress  # noqa: E402


def main():
    dist = ROOT / "native/dist"
    output = ROOT / "native/review"
    output.mkdir(exist_ok=True)
    results = {
        "checks": [],
        "console_errors": [],
        "page_errors": [],
        "external_requests": [],
    }

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/stockroom-to-statements/"):
                self.path = self.path[len("/stockroom-to-statements") :]
            super().do_GET()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(dist))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/stockroom-to-statements/js/"

    def passed(name):
        results["checks"].append({"name": name, "status": "passed"})
        print("PASSED:", name, flush=True)

    def loaded(page):
        page.locator("html[data-ready=true][data-saving=false]").wait_for(timeout=15000)
        expect(page).to_have_title("Stockroom to Statements")
        words = (
            page.locator("body").inner_text()
            + " "
            + page.locator("[aria-label],[title],meta[content]").evaluate_all(
                "nodes=>nodes.flatMap(n=>['aria-label','title','content'].map(k=>n.getAttribute(k)||'')).join(' ')"
            )
        )
        assert not re.search(r"\b(pilot|preview|prototype|experimental)\b", words, re.I)
        assert not page.locator("#save-error:not([hidden])").count()

    def settle(page, predicate=lambda s, v: True, timeout=30):
        loaded(page)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)
        state = decode_snapshot(query.get("progress", [None])[0])
        view = query.get("view", [None])[0]
        assert state is not None, (
            "Native URL must be accepted by original Python snapshot validator"
        )
        assert predicate(state, view), "Expected saved view/state"
        return state

    def click(page, label):
        page.get_by_role("button", name=label, exact=True).click()
        return settle(page)

    def select(page, answer, key=None):
        page.get_by_role("radio", name=answer, exact=True).check()
        settle(page)

    def readonly(page):
        expect(
            page.get_by_text(
                "Review only. Return to your current page to continue the activity.",
                exact=True,
            )
        ).to_be_visible()
        assert page.get_by_role("radio").count() == 0
        assert page.locator("main input").count() == 0
        assert page.locator("main .primary").count() == 0
        expect(
            page.get_by_role("button", name="Start over", exact=True)
        ).to_be_disabled()

    def layout(page, name):
        boxes = [
            page.get_by_role("button", name=label, exact=True).bounding_box()
            for label in ("Back", "Forward")
        ]
        assert all(44 <= b["width"] <= 45 and 44 <= b["height"] <= 45 for b in boxes), (
            boxes
        )
        assert abs(boxes[0]["y"] - boxes[1]["y"]) <= 1
        main_box = page.locator(".block-container").bounding_box()
        assert boxes[0]["x"] > main_box["x"] + main_box["width"] / 2
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        results.setdefault("navigation_layout", {})[name] = boxes

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            proxy={"server": "http://127.0.0.1:9", "bypass": "127.0.0.1,localhost"},
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})

        def watch(page):
            page.on("pageerror", lambda e: results["page_errors"].append(str(e)))

            def console(m):
                if m.text.startswith("BROWSER_VERSIONS="):
                    results["runtime"] = json.loads(m.text.split("=", 1)[1])
                elif m.type == "error":
                    results["console_errors"].append(m.text)

            page.on("console", console)
            page.on(
                "request",
                lambda r: results["external_requests"].append(r.url)
                if r.url.startswith("http")
                and not r.url.startswith(url.split("/stockroom-to-statements/js/")[0])
                else None,
            )
            return page

        page = watch(context.new_page())
        try:
            start = time.monotonic()
            page.goto(url, wait_until="domcontentloaded")
            loaded(page)
            results["initial_render_seconds"] = round(time.monotonic() - start, 2)
            results["runtime"] = "native HTML/CSS/JavaScript; no installation"
            expect(page.get_by_role("button", name="Back", exact=True)).to_be_disabled()
            expect(
                page.get_by_role("button", name="Forward", exact=True)
            ).to_be_disabled()
            layout(page, "desktop")
            page.screenshot(path=str(output / "briefing.png"), full_page=True)
            passed(
                "Packaged native runtime, final title, project /js/ assets and desktop layout"
            )
            click(page, START)
            page.locator("fieldset").first.wait_for()
            first = PLAN[0]["items"][0]
            click(page, PLAN[0]["check"])
            assert page.get_by_role("radio").count() > 0
            expect(
                page.get_by_role("button", name="Forward", exact=True)
            ).to_be_disabled()
            wrong = next(x for x in first.options if x != first.correct)
            select(page, wrong)
            failed = click(page, PLAN[0]["check"])
            page.reload(wait_until="domcontentloaded")
            loaded(page)
            assert settle(page) == failed
            assert page.get_by_role("radio", name=wrong, exact=True).is_checked()
            revised = page.get_by_role("button").filter(has_text="Check revised").first
            select(page, first.correct)
            state = click(page, revised.inner_text())
            expect(
                page.get_by_role("button", name="Forward", exact=True)
            ).to_be_disabled()
            for _ in range(3):
                click(page, "Back")
                readonly(page)
                if page.get_by_role("table").count():
                    page.set_viewport_size({"width": 390, "height": 844})
                    layout(page, "narrow-evidence-table")
                    page.screenshot(
                        path=str(output / "evidence-table-narrow.png"), full_page=True
                    )
                    page.set_viewport_size({"width": 1280, "height": 900})
                assert settle(page) == state
                click(page, "Forward")
                assert settle(page) == state
            back = page.get_by_role("button", name="Back", exact=True)
            page.get_by_role("button", name="Continue", exact=True).focus()
            page.keyboard.press("Shift+Tab")
            expect(back).to_be_focused()
            assert back.evaluate("e=>e.matches(':focus-visible')")
            assert back.evaluate("e=>getComputedStyle(e).outlineWidth") == "2px"
            page.keyboard.press("Enter")
            settle(page, lambda s, v: v == "0")
            readonly(page)
            page.get_by_role("button", name="Forward", exact=True).focus()
            page.keyboard.press("Enter")
            settle(page, lambda s, v: v == "1")
            passed(
                "Missing selection; deliberate wrong answer; refresh; revision; repeated immutable review; keyboard"
            )
            click(page, "Continue")
            second = PLAN[0]["items"][1]
            select(page, second.correct)
            draft = settle(page)
            order = page.locator("fieldset label").all_text_contents()
            click(page, "Back")
            readonly(page)
            bookmark = page.url
            page.reload(wait_until="domcontentloaded")
            loaded(page)
            readonly(page)
            assert settle(page) == draft
            clone = watch(context.new_page())
            clone.goto(bookmark, wait_until="domcontentloaded")
            loaded(clone)
            readonly(clone)
            assert settle(clone) == draft
            click(clone, "Forward")
            assert clone.get_by_role(
                "radio", name=second.correct, exact=True
            ).is_checked()
            assert clone.locator("fieldset label").all_text_contents() == order
            clone.goto(
                clone.url.replace("view=2", "view=999"), wait_until="domcontentloaded"
            )
            loaded(clone)
            settle(clone, lambda s, v: v == "2")
            expect(
                clone.get_by_role("button", name="Forward", exact=True)
            ).to_be_disabled()
            clone.close()
            click(page, "Forward")
            passed(
                "Drafts and stable shuffle preserved in review bookmarks; future-view rejected"
            )
            for plan_index, step in enumerate(PLAN):
                if step["kind"] == "choice":
                    for index, item in enumerate(step["items"]):
                        if plan_index == 0 and index == 0:
                            continue
                        select(page, item.correct)
                        click(page, step["check"])
                        click(
                            page,
                            step["final"]
                            if index == len(step["items"]) - 1
                            else "Continue",
                        )
                else:
                    # Supply required conceptual choices, then deliberately submit wrong numeric work.
                    for key, value in step["radios"]:
                        select(page, value, key)
                    click(page, step["check"])
                    expect(
                        page.get_by_role("button", name="Forward", exact=True)
                    ).to_be_disabled()
                    wrong_state = settle(page)
                    page.set_viewport_size({"width": 390, "height": 844})
                    layout(page, f"narrow-numeric-{plan_index}")
                    page.screenshot(
                        path=str(output / f"numeric-{plan_index}-narrow.png"),
                        full_page=True,
                    )
                    page.set_viewport_size({"width": 1280, "height": 900})
                    revised = (
                        page.get_by_role("button")
                        .filter(has_text="Check revised")
                        .first
                    )
                    click(page, revised.inner_text())
                    assert settle(page) == wrong_state
                    first_key = next(iter(step["values"]))
                    if step["prefix"] == "widget_cost_":
                        page.get_by_role("tab", name="FIFO", exact=True).click()
                    draft_field = page.locator("#" + step["prefix"] + first_key)
                    draft_field.fill("12,3")
                    loaded(page)
                    page.reload(wait_until="domcontentloaded")
                    loaded(page)
                    if step["prefix"] == "widget_cost_":
                        page.get_by_role("tab", name="FIFO", exact=True).click()
                    expect(
                        page.locator("#" + step["prefix"] + first_key)
                    ).to_have_value("12,3")
                    before = settle(page)
                    click(page, revised.inner_text())
                    assert settle(page) == before
                    if page.get_by_role("table").count():
                        saved = settle(page)
                        with page.expect_download() as event:
                            click(page, "Download table as CSV")
                        download = event.value
                        assert not re.search(
                            r"pilot|preview|prototype",
                            download.suggested_filename,
                            re.I,
                        )
                        evidence = output / f"stage-{plan_index}-table.csv"
                        download.save_as(str(evidence))
                        evidence.write_text(evidence.read_text())
                        assert evidence.read_text().strip()
                        assert settle(page) == saved
                        click(page, "Expand table")
                        expect(page.get_by_role("dialog")).to_be_visible()
                        click(page, "Close table")
                        assert settle(page) == saved
                    for key, value in step["values"].items():
                        if step["prefix"] == "widget_cost_":
                            tab = (
                                "FIFO"
                                if key.startswith("fifo_")
                                else "LIFO"
                                if key.startswith("lifo_")
                                else "Average cost"
                            )
                            page.get_by_role("tab", name=tab, exact=True).click()
                        field = page.locator("#" + step["prefix"] + key)
                        field.fill(str(value))
                        settle(page)
                    for key, value in step["radios"]:
                        select(page, value, key)
                    check = (
                        page.get_by_role("button")
                        .filter(has_text="Check revised")
                        .first
                    )
                    if check.count():
                        click(page, check.inner_text())
                    else:
                        click(page, step["check"])
                    if step["final"]:
                        click(page, step["final"])
            state = settle(page, lambda s, v: v == str(len(POSITIONS) - 1))
            results["score"] = score_summary(state)
            page.screenshot(path=str(output / "completed.png"), full_page=True)
            passed(
                "Complete lesson including all decisions, numeric gates, wrong calculations, revisions and scoring"
            )
            for position in range(len(POSITIONS) - 2, -1, -1):
                click(page, "Back")
                settle(page, lambda s, v: v == str(position))
                readonly(page)
                if page.get_by_role("table").count():
                    page.set_viewport_size({"width": 390, "height": 844})
                    layout(page, "narrow-evidence-table")
                    page.screenshot(
                        path=str(output / "evidence-table-narrow.png"), full_page=True
                    )
                    page.set_viewport_size({"width": 1280, "height": 900})
                if position == 1:
                    page.screenshot(path=str(output / "review.png"), full_page=True)
                assert settle(page) == state
            for position in range(1, len(POSITIONS)):
                click(page, "Forward")
                settle(page, lambda s, v: v == str(position))
                assert settle(page) == state
            page.set_viewport_size({"width": 390, "height": 844})
            layout(page, "narrow")
            page.screenshot(path=str(output / "narrow.png"), full_page=True)
            passed(
                "Entire reached lesson reviewed both directions without progress changes; 390px layout"
            )
            independent = watch(context.new_page())
            independent.goto(url, wait_until="domcontentloaded")
            loaded(independent)
            settle(independent, lambda s, v: v == "0")
            independent.close()
            context2 = browser.new_context()
            isolated = watch(context2.new_page())
            isolated.goto(url, wait_until="domcontentloaded")
            loaded(isolated)
            settle(isolated, lambda s, v: v == "0")
            context2.close()
            page.get_by_role("button", name="Start over", exact=True).click()
            settle(page, lambda s, v: v == "0")
            page.reload(wait_until="domcontentloaded")
            loaded(page)
            settle(page, lambda s, v: v == "0")
            page.goto(url + "?progress=invalid&view=999", wait_until="domcontentloaded")
            loaded(page)
            settle(page, lambda s, v: v == "0")
            passed(
                "Separate tabs and contexts; reset and refreshed new game; invalid snapshot and future rejected"
            )
            fixtures = json.loads(
                (ROOT / "native/tests/python-oracles.json").read_text()
            )
            legacy = watch(context.new_page())
            for fixture in fixtures["snapshots"]:
                legacy.goto(
                    url + "?progress=" + fixture["token"] + "&view=999",
                    wait_until="domcontentloaded",
                )
                loaded(legacy)
                restored = settle(legacy)
                assert restored == progress.validate_snapshot(fixture["payload"])
                expect(
                    legacy.get_by_role("button", name="Forward", exact=True)
                ).to_be_disabled()
            legacy.close()
            passed(
                "Original saved links for every stage restore without unlocking future views"
            )
            measurements = []
            for _ in range(5):
                cold = browser.new_context()
                p = watch(cold.new_page())
                session = cold.new_cdp_session(p)
                session.send("Network.setCacheDisabled", {"cacheDisabled": True})
                p.goto(url, wait_until="domcontentloaded")
                loaded(p)
                measurements.append(
                    p.evaluate(
                        "performance.getEntriesByName('lesson-ready')[0].startTime"
                    )
                )
                cold.close()
            results["cold_initializations_ms"] = measurements
            results["cold_median_ms"] = statistics.median(measurements)
            results["measurement_scope"] = (
                "Five cache-disabled fresh Chromium contexts on local loopback; no hosted, school-network, physical-device or class-capacity claim."
            )
            results["package_bytes"] = json.loads(
                (dist / "js/manifest.json").read_text()
            )["application_bytes"]
            passed("Five local cold initializations with no runtime installation")
            assert not results["page_errors"]
            assert not results["console_errors"]
            assert not results["external_requests"]
            passed("No external requests, console errors or page execution errors")
            results["status"] = "passed"
        except Exception:
            results["status"] = "failed"
            results["failure"] = traceback.format_exc()
            page.screenshot(path=str(output / "failure.png"), full_page=True)
            print(results["failure"], flush=True)
        finally:
            (output / "browser-results.json").write_text(
                json.dumps(results, indent=2) + "\n"
            )
            browser.close()
            server.shutdown()
    if results["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
