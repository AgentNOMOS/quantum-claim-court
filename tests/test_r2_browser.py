"""Headless Chromium tests of the UQCC-R2 app (system chromium + playwright, mocked Qollab bridge).

The bridge mock returns fixture strings produced by the REAL Python bridge (dev/make_fixtures.py).
Real Qollab acceptance still requires the owner's run.
"""
import html
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "dev"))
import build_r2_zip  # noqa: E402
import serve  # noqa: E402

pw = pytest.importorskip("playwright.sync_api")
import os  # noqa: E402

CHROMIUM = os.environ.get("UQCC_CHROMIUM", "/usr/bin/chromium")
if not pathlib.Path(CHROMIUM).exists():
    pytest.skip("Chromium not found: set UQCC_CHROMIUM to a Chromium/Chrome binary", allow_module_level=True)

FIX = {n: (ROOT / "dev/fixtures" / f"{n}.txt").read_text() for n in ("ok", "disputed", "refused", "error")}


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("site")
    build_r2_zip.stage(root / "stage")
    (root / "dev").mkdir()
    shutil.copy(ROOT / "dev/mock_bridge.js", root / "dev/mock_bridge.js")
    shutil.copytree(ROOT / "dev/fixtures", root / "dev/fixtures")
    httpd, base = serve.serve(root)
    yield root, base
    httpd.shutdown()


def harness(base, fixture="ok", with_backend=True):
    frag = (pathlib.Path(build_r2_zip.ROOT) / "app/index.html").read_text()
    backend = "window.backend = {mock: true};" if with_backend else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="importmap">{{"imports":{{"uqcc_app.js_api":"{base}/dev/mock_bridge.js"}}}}</script>
<link rel="stylesheet" href="{base}/stage/main.css">
<script>window.__FIXTURE="{fixture}"; window.__FIXTURE_BASE="{base}/dev/fixtures/"; {backend}</script>
</head><body style="margin:0">{frag}<script type="module" src="{base}/stage/main.js"></script></body></html>"""


def write_page(site, name, text):
    root, base = site
    (root / name).write_text(text)
    return f"{base}/{name}"


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        yield b
        b.close()


def open_app(browser, site, fixture="ok", width=1280, with_backend=True, perms=None):
    ctx = browser.new_context(viewport={"width": width, "height": 900})
    if perms:
        ctx.grant_permissions(perms)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(write_page(site, f"h_{fixture}_{int(with_backend)}.html", harness(site[1], fixture, with_backend)))
    page.wait_for_selector("#run-status.status-live, #run-status.status-failed", timeout=15000)
    return ctx, page, errors


def calls(page):
    return page.evaluate("globalThis.__bridgeCalls || []")


def env(name="ok"):
    return json.loads(FIX[name])


def verify_text(text, tmp_path):
    f = tmp_path / "evidence.txt"
    f.write_bytes(text.encode("utf-8"))
    stage = tmp_path / "pkg"
    build_r2_zip.stage(stage)
    return subprocess.run([sys.executable, "-I", str(stage / "verifier/verify_uqcc_r2.py"), str(f), str(stage)],
                          capture_output=True, text=True)


# ---------------------------------------------------------------- live render

def test_live_render_one_call(browser, site):
    ctx, page, errors = open_app(browser, site)
    try:
        assert errors == []
        assert "LIVE" in page.inner_text("#run-status")
        assert calls(page) == [{"fn": "run_court", "nargs": 1, "backendIsMock": True}]
        assert page.locator("#docket .docket-item").count() == 18
        e = env()
        ev = json.loads(e["r1_evidence_text"])
        for key in ("00", "01", "10", "11"):
            cell = page.locator(f'#counts tr[data-key="{key}"] td.num').inner_text()
            assert cell == str(ev["counts"].get(key, 0))
        assert ev["backend"]["name"] in page.inner_text("#backend-name")
        assert page.locator("#crosscheck li.bad").count() == 0
        assert page.locator("#crosscheck li.ok").count() >= 9
        assert page.input_value("#export") == e["export_text"]          # byte-exact display
        for k in ("A", "B", "AB"):
            assert ev["measurement"]["observables"][k]["estimate"] in page.inner_text(f'#fid-chart [data-obs="{k}"]')
    finally:
        ctx.close()


def test_interactions_never_call_bridge_again(browser, site):
    ctx, page, _ = open_app(browser, site)
    try:
        page.click('#docket .docket-item[data-id="RT6"] button')
        assert "RT6" in page.inner_text("#claim-detail") and "BLOCKED" in page.inner_text("#claim-detail").upper()
        page.click('#docket-filters button[data-filter="DISPUTED"]')
        assert page.locator("#docket .docket-item").count() == 2          # V2, V4 on a consistent run
        page.click('#docket-filters button[data-filter="MEASUREMENT"]')
        assert sorted(page.eval_on_selector_all("#docket .docket-item", "els => els.map(e => e.dataset.id)")) == \
            ["C1", "V1", "V2", "V3", "V4"]
        page.click('#witness-table .wt-row[data-id="RT7"]')
        assert page.input_value("#claim-select") == "RT7"
        page.select_option("#claim-select", "V2")
        assert "PERMISSIBLE REVISED CLAIM" in page.inner_text("#claim-detail").upper()
        ch = json.loads(env()["court_text"])["challenge"]
        cells = {(m[0], m[1], m[2]): m[3] for m in ch["matrix"]}
        for s, c, f in [("S3", "DJ92", "as_stated"), ("S3", "BDEFMS98", "as_stated"), ("S1", "WZ82", "run_proves"),
                        ("S4", "WZ82", "as_stated"), ("S2", "WRONGMAP", "as_stated"), ("S3", "BH96", "as_stated")]:
            page.select_option("#ch-statement", s)
            page.select_option("#ch-citation", c)
            page.select_option("#ch-framing", f)
            out = page.locator("#challenge-out .local-result")
            assert out.get_attribute("data-verdict") == cells[(s, c, f)]
            assert "LOCAL EVALUATION" in out.inner_text()
        assert len(calls(page)) == 1
        assert page.input_value("#export") == env()["export_text"]       # evidence unchanged
    finally:
        ctx.close()


def test_literature_claims_not_presented_as_measured(browser, site):
    ctx, page, _ = open_app(browser, site)
    try:
        for cid in ("C2", "C3", "RT3", "RT9"):
            page.select_option("#claim-select", cid)
            assert "Not used: this claim is not decided by measurement" in page.inner_text("#claim-detail")
    finally:
        ctx.close()


# ---------------------------------------------------------------- responsive

@pytest.mark.parametrize("width", [1280, 820, 375, 320])
def test_responsive_no_overflow_no_hidden_controls(browser, site, width):
    ctx, page, _ = open_app(browser, site, width=width)
    try:
        assert page.evaluate("document.documentElement.scrollWidth") <= width
        bad = page.evaluate("""(w) => {
          const out = [];
          for (const el of document.querySelectorAll('button, select, textarea, a, .fid-track, .verdict, .chip')) {
            if (el.closest('.scroll-x')) continue;
            const r = el.getBoundingClientRect();
            const st = getComputedStyle(el);
            if (st.display === 'none' || st.visibility === 'hidden') { out.push('hidden:' + el.outerHTML.slice(0, 60)); continue; }
            if (r.width < 1 || r.height < 1) { out.push('zero:' + el.outerHTML.slice(0, 60)); continue; }
            if (r.left < -0.5 || r.right > w + 0.5) out.push('clip:' + el.outerHTML.slice(0, 60));
          }
          return out;
        }""", width)
        assert bad == []
        # the measurement chart is fully inside the viewport and its markers inside their tracks
        inside = page.evaluate("""() => [...document.querySelectorAll('.fid-track')].every(t => {
          const r = t.getBoundingClientRect();
          return [...t.children].every(c => { const q = c.getBoundingClientRect();
            return q.left >= r.left - 8 && q.right <= r.right + 8; }); })""")
        assert inside
    finally:
        ctx.close()


# ---------------------------------------------------------------- failure states

@pytest.mark.parametrize("fixture,with_backend,ncalls", [
    ("refused", True, 1), ("error", True, 1), ("reject", True, 1), ("garbage", True, 1), ("ok", False, 0)])
def test_failure_states_show_no_fake_results(browser, site, fixture, with_backend, ncalls):
    ctx, page, _ = open_app(browser, site, fixture=fixture, with_backend=with_backend)
    try:
        assert "status-failed" in page.get_attribute("#run-status", "class")
        assert page.is_visible("#failure")
        assert len(calls(page)) == ncalls
        assert page.locator("#docket .docket-item").count() == 0
        body = page.inner_text("main")
        assert "/2000" not in body and "LIVE" not in page.inner_text("#run-status")
        assert page.input_value("#export").startswith("No evidence")
        assert page.is_disabled("#btn-copy")
        if fixture in ("error", "reject"):
            assert "NOT retried" in page.inner_text("#failure")
    finally:
        ctx.close()


def test_statistical_disagreement_rendered(browser, site):
    ctx, page, _ = open_app(browser, site, fixture="disputed")
    try:
        assert page.get_attribute('#docket .docket-item[data-id="C1"]', "data-verdict") == "DISPUTED"
        assert page.get_attribute('#docket .docket-item[data-id="V1"]', "data-verdict") == "DISPUTED"
        assert page.get_attribute('#docket .docket-item[data-id="C3"]', "data-verdict") == "SUPPORTED"
        assert "EXCLUDES" in page.inner_text('#fid-chart [data-obs="A"]')
        page.select_option("#claim-select", "V1")
        assert "1.4%" in page.inner_text("#claim-detail")
    finally:
        ctx.close()


# ---------------------------------------------------------------- export / clipboard

def test_clipboard_copy_is_exact_and_verifies(browser, site, tmp_path):
    ctx, page, _ = open_app(browser, site, perms=["clipboard-read", "clipboard-write"])
    try:
        page.click("#btn-copy")
        page.wait_for_function("document.getElementById('copy-msg').dataset.method")
        assert page.get_attribute("#copy-msg", "data-method") == "clipboard"
        copied = page.evaluate("navigator.clipboard.readText()")
        assert copied == env()["export_text"]
        r = verify_text(copied, tmp_path)
        assert r.returncode == 0, r.stdout
        assert json.loads(r.stdout)["challenge_cells_verified"] == 84
    finally:
        ctx.close()


def test_textarea_export_verifies_and_disputed_is_flagged(browser, site, tmp_path):
    for fixture, rc in (("ok", 0), ("disputed", 2)):
        ctx, page, _ = open_app(browser, site, fixture=fixture)
        try:
            r = verify_text(page.input_value("#export"), tmp_path)
            assert r.returncode == rc, r.stdout
        finally:
            ctx.close()


def test_sandboxed_null_origin_frame_and_clipboard_fallback(browser, site):
    root, base = site
    outer = (f'<!doctype html><html><body style="margin:0"><iframe id="f" sandbox="allow-scripts" '
             f'style="width:375px;height:900px;border:0" srcdoc="{html.escape(harness(base), quote=True)}"></iframe></body></html>')
    ctx = browser.new_context(viewport={"width": 420, "height": 950})
    page = ctx.new_page()
    try:
        page.goto(write_page(site, "outer.html", outer))
        frame = page.frame_locator("#f")
        frame.locator("#run-status.status-live").wait_for(timeout=15000)
        f = page.frames[1]
        assert f.evaluate("String(window.origin)") == "null"
        assert len(f.evaluate("globalThis.__bridgeCalls")) == 1
        frame.locator("#btn-copy").click()
        f.wait_for_function("document.getElementById('copy-msg').dataset.method")
        method = frame.locator("#copy-msg").get_attribute("data-method")
        assert method in ("execCommand", "manual")
        sel = f.evaluate("(() => { const t = document.getElementById('export'); return [t.selectionStart, t.selectionEnd, t.value.length]; })()")
        assert sel[0] == 0 and sel[1] == sel[2]
        assert frame.locator("#crosscheck li.bad").count() == 0       # pure-JS SHA works without crypto.subtle
    finally:
        ctx.close()
