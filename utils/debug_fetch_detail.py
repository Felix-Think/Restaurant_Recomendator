"""Debug helper: load first record in CSV and fetch its detail page HTML."""

from __future__ import annotations

import csv
from pathlib import Path

from playwright.sync_api import sync_playwright

CSV_PATH = Path("data/foody_page1.5.csv")
OUTPUT_HTML = Path("data/debug_detail.html")


def fetch_html(url: str, wait_ms: int = 4000) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    with CSV_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        first = next(reader, None)
    if not first:
        raise ValueError("CSV is empty.")

    detail_url = first.get("detail_url")
    if not detail_url:
        raise ValueError("First row has no detail_url.")

    html = fetch_html(detail_url)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Saved detail HTML to {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
