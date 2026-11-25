"""Screenshots of the six brief questions answered in the running Streamlit app (streamlit run app.py),
plus the summary report. Output: results/screenshots/*.png"""
import re, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_tests import QS  # noqa: E402  (QS only; run_tests guards its main loop below)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/screenshots"; OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8502"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    pg.goto(URL); pg.get_by_placeholder("Ask about your emissions data").wait_for(timeout=120_000)
    for i, (tag, q) in enumerate(QS, 1):
        pg.get_by_role("button", name="New conversation").click(); time.sleep(2)
        box = pg.get_by_placeholder("Ask about your emissions data"); box.fill(q); box.press("Enter")
        pg.get_by_text("How I got this").first.wait_for(timeout=300_000); time.sleep(2)
        msg = pg.locator('[data-testid="stChatMessage"]').last
        msg.screenshot(path=OUT / f"{i:02d}_{re.sub(r'\W+', '_', tag.lower())}_answer.png")
        pg.screenshot(path=OUT / f"{i:02d}_{re.sub(r'\W+', '_', tag.lower())}_full.png", full_page=True)
        print("done", tag, flush=True)
    rep = sorted((ROOT / "projects/demo-company/reports").glob("summary-*.html"))
    if rep:
        pg.goto(rep[-1].as_uri()); time.sleep(3)
        pg.screenshot(path=OUT / "07_summary_report.png", full_page=True)
        pg.emulate_media(color_scheme="dark"); time.sleep(1)
        pg.screenshot(path=OUT / "08_summary_report_dark.png", full_page=True)
        m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        m.goto(rep[-1].as_uri()); time.sleep(3)
        m.screenshot(path=OUT / "09_summary_report_mobile.png", full_page=True)
        print("done report", rep[-1].name)
    b.close()
