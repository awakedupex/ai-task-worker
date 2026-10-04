"""Browser tool via Playwright on the LOCAL mock ERP UI.
Proves browser use without flaky external sites. Falls back to erp_api on failure."""
import os
from tools.base import Tool, Observation

ERP_BASE = os.getenv("ERP_BASE_URL", "http://localhost:8000")


class BrowserOpenTool(Tool):
    name = "erp_browser.open"
    description = "Open the mock ERP web UI in a real browser (Playwright). Returns title + screenshot path."
    schema = {"type": "object", "properties": {"url": {"type": "string"}}}

    def execute(self, args):
        url = args.get("url") or f"{ERP_BASE}/ui"
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                pg = b.new_page()
                pg.goto(url, timeout=10000)
                title = pg.title()
                os.makedirs("trajectory_logs", exist_ok=True)
                shot = "trajectory_logs/erp_ui.png"
                pg.screenshot(path=shot)
                b.close()
            return Observation(ok=True, data={"url": url, "title": title},
                               evidence={"screenshot": shot})
        except Exception as e:
            return Observation(ok=False, error=f"browser open failed ({e}); use erp_api.create instead")


class BrowserFillSubmitTool(Tool):
    name = "erp_browser.submit"
    description = "Fill + submit the ERP web form via browser. Args: vendor, amount, due_date."
    schema = {"type": "object", "properties": {
        "vendor": {"type": "string"}, "amount": {"type": "number"}, "due_date": {"type": "string"}}}

    def execute(self, args):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                pg = b.new_page()
                pg.goto(f"{ERP_BASE}/ui", timeout=10000)
                pg.fill("#vendor", str(args.get("vendor", "")))
                pg.fill("#amount", str(args.get("amount", "")))
                pg.fill("#due", str(args.get("due_date", "")))
                pg.click("#submit")
                pg.wait_for_timeout(800)
                body = pg.content()[:2000]
                os.makedirs("trajectory_logs", exist_ok=True)
                shot = "trajectory_logs/erp_submit.png"
                pg.screenshot(path=shot)
                b.close()
            # record in DB too (server does it); fetch latest to get id
            from tools.erp_api import _connect
            con = _connect()
            row = con.execute("SELECT id FROM invoices ORDER BY id DESC LIMIT 1").fetchone()
            con.close()
            eid = row[0] if row else None
            return Observation(ok=True, data={"erp_id": eid, "via": "browser"},
                               evidence={"screenshot": shot})
        except Exception as e:
            return Observation(ok=False, error=f"browser submit failed ({e}); fallback to erp_api.create")
