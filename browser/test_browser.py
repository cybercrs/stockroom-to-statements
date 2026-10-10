"""Run complete lessons in actual stlite, with external network traffic blocked."""

from __future__ import annotations
import json
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser.scenario import START, PLAN, POSITIONS, decode_snapshot, score_summary

ROOT = Path(__file__).resolve().parents[1]


def main():
    dist = ROOT / "browser/dist"
    output = ROOT / "browser/test-results"
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
            if self.path.startswith("/lesson/"):
                self.path = self.path[len("/lesson") :]
            if self.path == "/app.json":
                config = json.loads((dist / "app.json").read_text())
                config["files"]["browser/app.py"] += (
                    '\nimport sys,json,pyodide\nprint("BROWSER_VERSIONS="+json.dumps({"python":sys.version.split()[0],"streamlit":st.__version__,"pyodide":pyodide.__version__}))\n'
                )
                data = json.dumps(config).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                super().do_GET()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(dist))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/lesson/"

    def passed(name):
        results["checks"].append({"name": name, "status": "passed"})
        print("PASSED:", name, flush=True)

    def loaded(page):
        page.get_by_role("button", name="Back", exact=True).wait_for(timeout=120000)
        settle(page)

    def settle(page, predicate=lambda s, v: True, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            assert page.locator('[data-testid="stException"]').count() == 0, (
                page.locator('[data-testid="stException"]').all_text_contents()
            )
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)
            state = decode_snapshot(query.get("progress", [None])[0])
            view = query.get("view", [None])[0]
            idle = page.locator('[data-test-script-state="notRunning"]').count() > 0
            if state is not None and idle and predicate(state, view):
                page.wait_for_timeout(150)
                return state
            page.wait_for_timeout(50)
        raise AssertionError(f"Expected rendered saved state: {page.url}")

    def click(page, label):
        old = page.url
        empty = (
            label.startswith("Check")
            and page.get_by_role("radio").count() > 0
            and page.get_by_role("radio", checked=True).count() == 0
        )
        page.locator('[data-testid="stMain"]').get_by_role(
            "button", name=label, exact=True
        ).click()
        if empty:
            page.locator('[data-testid="stAlert"]').last.wait_for()
            return settle(page)
        return settle(page, lambda s, v: page.url != old)

    def select(page, answer, key=None):
        container = page.locator(".st-key-" + key) if key else page
        radio = page.get_by_role("radio", name=answer, exact=True)
        if radio.is_checked():
            return
        old = page.url
        container.locator("label").filter(has=radio).click()
        settle(page, lambda s, v: page.url != old)

    def readonly(page):
        expect(
            page.get_by_text(
                "Review only. Return to your current page to continue the activity.",
                exact=True,
            )
        ).to_be_visible()
        assert page.get_by_role("radio").count() == 0
        assert page.get_by_role("spinbutton").count() == 0
        expect(
            page.locator('[data-testid="stMain"] .stButton').get_by_role("button")
        ).to_have_count(2)
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
                and not r.url.startswith(url.split("/lesson/")[0])
                else None,
            )
            return page

        page = watch(context.new_page())
        try:
            start = time.monotonic()
            page.goto(url, wait_until="domcontentloaded")
            loaded(page)
            results["initial_render_seconds"] = round(time.monotonic() - start, 2)
            assert results["runtime"]["streamlit"] == "1.57.0"
            assert results["runtime"]["pyodide"] == "0.29.3"
            expect(page.get_by_role("button", name="Back", exact=True)).to_be_disabled()
            expect(
                page.get_by_role("button", name="Forward", exact=True)
            ).to_be_disabled()
            layout(page, "desktop")
            page.screenshot(path=str(output / "briefing.png"), full_page=True)
            passed(
                "Pinned Wasm runtime; local subdirectory assets; initial navigation and layout"
            )
            click(page, START)
            page.locator("[data-testid=stRadio]").first.wait_for()
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
            order = page.locator("[data-testid=stRadio] label").all_text_contents()
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
            assert (
                clone.locator("[data-testid=stRadio] label").all_text_contents()
                == order
            )
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
                        field = page.locator(
                            ".st-key-" + step["prefix"] + key
                        ).get_by_role("spinbutton")
                        old = page.url
                        field.fill(str(value))
                        field.press("Tab")
                        settle(page, lambda s, v: page.url != old)
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
            # Open the native sidebar on a narrow viewport and reset the current activity.
            page.locator("[data-testid=stExpandSidebarButton]").click()
            page.screenshot(path=str(output / "narrow-reset.png"), full_page=True)
            page.locator("[data-testid=stSidebar]").get_by_role(
                "button", name="Start over", exact=True
            ).click()
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
