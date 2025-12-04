"""Fetch and parse Foody detail pages (ShopeeFood) to extract metadata.

Steps:
- Fetch HTML via Playwright (JS rendered).
- Extract embedded JSON (window.__NUXT__) or ld+json.
- Parse key fields: name, address, rating, opening hours, price range, categories/tags, delivery/detail links.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.sync_api import sync_playwright


def fetch_html(url: str, output_path: Path) -> Path:
    """Fetch HTML of a Foody/ShopeeFood detail page and save to output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4000)  # allow JS to render
        html = page.content()
        output_path.write_text(html, encoding="utf-8")
        browser.close()
    return output_path


def _extract_nuxt_json(html: str) -> Optional[Dict[str, Any]]:
    """Extract window.__NUXT__ JSON blob from the HTML."""
    match = re.search(r"window.__NUXT__=(\{.*?\});", html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_ld_json(html: str) -> Optional[Dict[str, Any]]:
    """Extract first <script type='application/ld+json'> if present."""
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def parse_detail(html_path: Path) -> Dict[str, Any]:
    """Parse saved HTML to extract structured info."""
    html = html_path.read_text(encoding="utf-8")
    nuxt = _extract_nuxt_json(html)
    ld = _extract_ld_json(html)

    result: Dict[str, Any] = {
        "name": None,
        "address": None,
        "district": None,
        "city": None,
        "avg_rating": None,
        "rating_breakdown": {},
        "price_range": None,
        "opening_hours": None,
        "categories": [],
        "cuisines": [],
        "delivery_url": None,
        "detail_url": None,
        "latitude": None,
        "longitude": None,
    }

    # Try ld+json first for generic fields
    if ld:
        result["name"] = ld.get("name") or result["name"]
        result["address"] = ld.get("address", {}).get("streetAddress") or result["address"]
        result["avg_rating"] = ld.get("aggregateRating", {}).get("ratingValue") or result["avg_rating"]
        result["detail_url"] = ld.get("url") or result["detail_url"]
        result["price_range"] = ld.get("priceRange") or result["price_range"]
        if "geo" in ld:
            result["latitude"] = ld["geo"].get("latitude") or result["latitude"]
            result["longitude"] = ld["geo"].get("longitude") or result["longitude"]
        if "servesCuisine" in ld:
            cuisines = ld["servesCuisine"]
            if isinstance(cuisines, list):
                result["cuisines"] = [c for c in cuisines if c]
            elif cuisines:
                result["cuisines"] = [cuisines]

    # Nuxt blob often contains richer info; adjust paths after inspecting actual structure
    if nuxt:
        # Common pattern: data[0].restaurant or props.pageProps
        restaurant = None
        data = nuxt.get("data") or []
        if data:
            # heuristic: first dict containing "restaurant"
            for item in data:
                if isinstance(item, dict) and "restaurant" in item:
                    restaurant = item.get("restaurant")
                    break
        if not restaurant:
            # fallback for other shapes
            pass

        if isinstance(restaurant, dict):
            result["name"] = restaurant.get("name") or result["name"]
            result["address"] = restaurant.get("address") or result["address"]
            result["district"] = restaurant.get("district") or result["district"]
            result["city"] = restaurant.get("city") or result["city"]
            result["avg_rating"] = restaurant.get("rating") or result["avg_rating"]
            result["price_range"] = restaurant.get("priceRange") or result["price_range"]
            result["opening_hours"] = restaurant.get("opening") or result["opening_hours"]
            result["categories"] = restaurant.get("categories") or result["categories"]
            result["cuisines"] = restaurant.get("cuisines") or result["cuisines"]
            result["delivery_url"] = restaurant.get("deliveryUrl") or result["delivery_url"]
            result["detail_url"] = restaurant.get("detailUrl") or result["detail_url"]
            result["latitude"] = restaurant.get("latitude") or result["latitude"]
            result["longitude"] = restaurant.get("longitude") or result["longitude"]
            if restaurant.get("ratingDetails"):
                result["rating_breakdown"] = restaurant["ratingDetails"]

    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch and parse a Foody/ShopeeFood detail page.")
    parser.add_argument("--url", required=True, help="Foody detail URL")
    parser.add_argument("--html-out", default="data/detail.html", help="Path to save fetched HTML")
    parser.add_argument("--json-out", default="data/detail.json", help="Path to save parsed JSON")
    args = parser.parse_args()

    html_path = fetch_html(args.url, Path(args.html_out))
    parsed = parse_detail(html_path)

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved HTML to {html_path}")
    print(f"Saved parsed JSON to {json_path}")


if __name__ == "__main__":
    main()
