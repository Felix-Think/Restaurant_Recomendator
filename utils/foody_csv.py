import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.foody.vn"
DEFAULT_HTML_PATH = Path("data/foody_page1.html")
DEFAULT_CSV_PATH = Path("data/foody_page1.csv")
CSV_COLUMNS = [
    "restaurant_id",
    "name",
    "branch_name",
    "address",
    "district",
    "city",
    "avg_rating",
    "total_reviews",
    "has_delivery",
    "delivery_url",
    "detail_url",
    "cuisines",
    "categories",
    "latitude",
    "longitude",
    "price_range",
    "opening_hours",
    "rating_breakdown",
]


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return None


def _normalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return f"{BASE_URL}{url}" if url.startswith("/") else url


def _parse_json_from_html(html_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8")
    match = re.search(r"var\s+jsonData\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        raise ValueError("Không tìm thấy biến jsonData trong file HTML")
    return json.loads(match.group(1))


def _item_to_row(item: dict, parent_branch: Optional[str] = None) -> dict:
    cuisines = ", ".join(c["Name"] for c in item.get("Cuisines", []) if c.get("Name"))
    categories = ", ".join(c["Name"] for c in item.get("Categories", []) if c.get("Name"))
    return {
        "restaurant_id": item.get("Id"),
        "name": item.get("Name") or item.get("BranchName"),
        "branch_name": parent_branch or item.get("BranchName"),
        "address": item.get("Address"),
        "district": item.get("District"),
        "city": item.get("City"),
        "avg_rating": _safe_float(item.get("AvgRating")),
        "total_reviews": item.get("TotalReview"),
        "has_delivery": item.get("HasDelivery"),
        "delivery_url": _normalize_url(item.get("DeliveryUrl")),
        "detail_url": _normalize_url(item.get("DetailUrl")),
        "cuisines": cuisines,
        "categories": categories,
        "latitude": item.get("Latitude"),
        "longitude": item.get("Longitude"),
        "price_range": None,
        "opening_hours": None,
        "rating_breakdown": None,
    }


def _fetch_html(url: str, wait_ms: int = 4000) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000, wait_until="networkidle")
        try:
            page.wait_for_selector("div.micro-timesopen", timeout=5000)
        except Exception:
            pass
        try:
            page.wait_for_selector("span[itemprop='priceRange']", timeout=3000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return html


def _extract_nuxt_json(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"window.__NUXT__=(\{.*?\});", html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_init_data_main(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"var\s+initDataMain\s*=\s*(\{.*?\});", html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_ld_json(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _parse_price(soup: BeautifulSoup, html: str) -> Optional[str]:
    init_main = _extract_init_data_main(html)
    if init_main:
        min_price = init_main.get("PriceMin")
        max_price = init_main.get("PriceMax")
        if min_price and max_price:
            return f"{int(float(min_price))}-{int(float(max_price))}"
        if min_price:
            return str(int(float(min_price)))
        if max_price:
            return str(int(float(max_price)))

    price_block = soup.find("span", attrs={"itemprop": "priceRange"}) or soup.select_one("div.res-common-minmaxprice")
    if price_block:
        nums = re.findall(r"\d{1,3}(?:\.\d{3})*", price_block.get_text(" ", strip=True))
        if len(nums) >= 2 and all(x.replace(".", "").isdigit() for x in nums[:2]):
            low, high = nums[0].replace(".", ""), nums[1].replace(".", "")
            return f"{low}-{high}"
        if len(nums) == 1 and nums[0].replace(".", "").isdigit():
            return nums[0].replace(".", "")
    match = re.search(r"(\d[\d\.]*)\s*(?:đ|₫)\s*-\s*(\d[\d\.]*)\s*(?:đ|₫)", html, flags=re.IGNORECASE)
    if match and match.group(1).replace(".", "").isdigit() and match.group(2).replace(".", "").isdigit():
        return f"{match.group(1).replace('.', '')}-{match.group(2).replace('.', '')}"
    return None


def _parse_opening_hours(soup: BeautifulSoup, html: str) -> Optional[str]:
    init_main = _extract_init_data_main(html)
    if init_main:
        time_ranges = init_main.get("TimeRanges") or []
        if time_ranges and isinstance(time_ranges, list):
            tr = time_ranges[0]
            start = tr.get("StartTime24h")
            end = tr.get("EndTime24h")
            if start and end:
                return f"{start} - {end}"

    time_block = soup.select_one("div.micro-timesopen")
    if time_block:
        match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", time_block.get_text(" ", strip=True))
        if match:
            return f"{match.group(1)} - {match.group(2)}"
    hours_match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", html)
    if hours_match:
        return f"{hours_match.group(1)} - {hours_match.group(2)}"
    return None


def _parse_rating_breakdown(soup: BeautifulSoup, html: str) -> Optional[Dict[str, float]]:
    init_main = _extract_init_data_main(html)
    if init_main and init_main.get("AvgPointList"):
        try:
            return {item["Label"]: float(item["Point"]) for item in init_main["AvgPointList"] if "Label" in item}
        except Exception:
            pass

    breakdown: Dict[str, float] = {}
    labels = [el.get_text(strip=True) for el in soup.select("#res-summary-point [class*=title]")]
    scores = [el.get_text(strip=True) for el in soup.select("#res-summary-point [class*=number]")]
    if labels and scores and len(labels) == len(scores):
        for lbl, sc in zip(labels, scores):
            try:
                breakdown[lbl] = float(sc.replace(",", "."))
            except ValueError:
                continue
    if not breakdown:
        patterns = [
            r'microsite-top-points_item_label[^>]*>([^<]+)<.*?microsite-top-points_item_score[^>]*>([\d\.]+)<',
            r'microsite-top-points_item_score[^>]*>([\d\.]+)<.*?microsite-top-points_item_label[^>]*>([^<]+)<',
        ]
        for pat in patterns:
            pairs = re.findall(pat, html, flags=re.DOTALL)
            for a, b in pairs:
                label, score = (a, b) if pat.startswith("micro") else (b, a)
                try:
                    breakdown[label.strip()] = float(score)
                except ValueError:
                    continue
    return breakdown or None


def _parse_detail_html(html: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"price_range": None, "opening_hours": None, "rating_breakdown": None}
    soup = BeautifulSoup(html, "html.parser")

    result["price_range"] = _parse_price(soup, html)
    result["opening_hours"] = _parse_opening_hours(soup, html)

    ld = _extract_ld_json(html)
    if ld:
        result["price_range"] = ld.get("priceRange") or result["price_range"]
        if "openingHours" in ld:
            result["opening_hours"] = ld["openingHours"]
        agg = ld.get("aggregateRating") or {}
        if agg.get("ratingValue") is not None:
            result.setdefault("avg_rating", agg.get("ratingValue"))

    nuxt = _extract_nuxt_json(html)
    if nuxt:
        data = nuxt.get("data") or []
        for item in data:
            if isinstance(item, dict) and "restaurant" in item:
                restaurant = item.get("restaurant")
                if isinstance(restaurant, dict):
                    result["price_range"] = restaurant.get("priceRange") or result["price_range"]
                    result["opening_hours"] = restaurant.get("opening") or result["opening_hours"]
                    if restaurant.get("ratingDetails"):
                        result["rating_breakdown"] = restaurant["ratingDetails"]
                    if restaurant.get("rating") is not None:
                        result.setdefault("avg_rating", restaurant.get("rating"))
                break

    if not result.get("rating_breakdown"):
        result["rating_breakdown"] = _parse_rating_breakdown(soup, html)

    return result


def _find_foody_link_in_shopee(html: str) -> Optional[str]:
    match = re.search(r"https?://www\.foody\.vn/[^\s\"'>]+", html)
    return match.group(0) if match else None


def _enrich_row_with_detail(row: dict) -> dict:
    foody_url = row.get("detail_url")
    if not foody_url and row.get("delivery_url"):
        try:
            shopee_html = _fetch_html(row["delivery_url"])
            foody_url = _find_foody_link_in_shopee(shopee_html)
        except Exception:
            foody_url = None

    if foody_url:
        try:
            detail_html = _fetch_html(foody_url)
            detail_data = _parse_detail_html(detail_html)
            for k, v in detail_data.items():
                if v:
                    if k == "rating_breakdown":
                        row[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        row[k] = v
            # update restaurant_id if present in initDataMain
            init_main = _extract_init_data_main(detail_html)
            if init_main and init_main.get("RestaurantID"):
                row["restaurant_id"] = init_main["RestaurantID"]
        except Exception:
            pass

    return row


def extract_restaurants(html_path: Path = DEFAULT_HTML_PATH, output_csv: Path = DEFAULT_CSV_PATH):
    """
    Đọc HTML trang kết quả Foody, trích xuất danh sách nhà hàng (bao gồm các chi nhánh),
    cố gắng vào Shopee/Foody detail để bổ sung price_range, opening_hours, rating_breakdown,
    và lưu thành file CSV.
    """
    data = _parse_json_from_html(html_path)

    rows = []
    for item in data.get("searchItems", []):
        rows.append(_item_to_row(item))
        for sub_item in item.get("SubItems", []):
            rows.append(_item_to_row(sub_item, parent_branch=item.get("Name") or item.get("BranchName")))

    enriched_rows = []
    for row in rows:
        enriched_rows.append(_enrich_row_with_detail(row))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"Đã trích xuất {len(enriched_rows)} nhà hàng vào {output_csv}")
    return enriched_rows


if __name__ == "__main__":
    extract_restaurants()
