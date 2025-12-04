"""Crawl menu items from delivery URLs and append to existing CSV."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def fetch_html(url: str, wait_ms: int = 4000) -> str:
    """Fetch a page with Playwright and return HTML."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html


def extract_menu_items(html: str, limit: int = 10) -> List[str]:
    """Best-effort extraction of menu item names from ShopeeFood/Foody detail HTML."""
    soup = BeautifulSoup(html, "html.parser")
    items: List[str] = []

    # Common ShopeeFood selectors
    selectors = [
        ".item-restaurant-name",  # legacy
        ".menu-name",  # common menu name class
        ".dish-name",
        ".title-food",
        ".item-name",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            name = el.get_text(" ", strip=True)
            if name and name not in items:
                items.append(name)
            if len(items) >= limit:
                return items

    # Fallback regex: find quoted dish names near price
    if len(items) < limit:
        patterns = [
            r'"Name"\s*:\s*"([^"]+)"',
            r'"name"\s*:\s*"([^"]+)"\s*,\s*"price"',
            r'"dishName"\s*:\s*"([^"]+)"',
            r'"displayName"\s*:\s*"([^"]+)"',
        ]
        matches: List[str] = []
        for pat in patterns:
            matches.extend(re.findall(pat, html))
        for m in matches:
            if m not in items:
                items.append(m)
            if len(items) >= limit:
                break

    return items[:limit]


def append_menu_to_csv(csv_path: Path, output_path: Path | None = None, limit: int = 10):
    """Read CSV, fetch menu items for each delivery_url, and append a menu_items column."""
    output_path = output_path or csv_path
    rows = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if "menu_items" not in fieldnames:
            fieldnames.append("menu_items")
        for row in reader:
            url = row.get("delivery_url")
            if url:
                try:
                    html = fetch_html(url)
                    menu_items = extract_menu_items(html, limit=limit)
                    row["menu_items"] = ", ".join(menu_items)
                except Exception:
                    row["menu_items"] = ""
            else:
                row["menu_items"] = ""
            rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated CSV with menu_items -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Append menu items to Foody CSV using delivery URLs.")
    parser.add_argument("--csv", default="data/foody_page1.csv", help="Input CSV path")
    parser.add_argument("--output", default=None, help="Output CSV path (default: overwrite input)")
    parser.add_argument("--limit", type=int, default=10, help="Max menu items to capture per restaurant")
    args = parser.parse_args()

    append_menu_to_csv(Path(args.csv), Path(args.output) if args.output else None, limit=args.limit)


if __name__ == "__main__":
    main()
