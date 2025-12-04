import csv
import json
import re
from pathlib import Path

BASE_URL = "https://www.foody.vn"
DEFAULT_HTML_PATH = Path("data/foody_page1.html")
DEFAULT_CSV_PATH = Path("data/foody_page1.csv")
CSV_COLUMNS = [
    "name",
    "branch_name",
    "address",
    "district",
    "city",
    "avg_rating",
    "total_reviews",
    "has_delivery",
    "has_booking",
    "delivery_url",
    "booking_url",
    "detail_url",
    "branch_url",
    "cuisines",
    "categories",
    "latitude",
    "longitude",
]


def _safe_float(value):
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return None


def _normalize_url(url):
    if not url:
        return None
    return f"{BASE_URL}{url}" if url.startswith("/") else url


def _parse_json_from_html(html_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8")
    match = re.search(r"var\s+jsonData\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        raise ValueError("Không tìm thấy biến jsonData trong file HTML")
    return json.loads(match.group(1))


def _item_to_row(item: dict, parent_branch: str | None = None) -> dict:
    cuisines = ", ".join(c["Name"] for c in item.get("Cuisines", []) if c.get("Name"))
    categories = ", ".join(c["Name"] for c in item.get("Categories", []) if c.get("Name"))

    return {
        "name": item.get("Name") or item.get("BranchName"),
        "branch_name": parent_branch or item.get("BranchName"),
        "address": item.get("Address"),
        "district": item.get("District"),
        "city": item.get("City"),
        "avg_rating": _safe_float(item.get("AvgRating")),
        "total_reviews": item.get("TotalReview"),
        "has_delivery": item.get("HasDelivery"),
        "has_booking": item.get("HasBooking"),
        "delivery_url": _normalize_url(item.get("DeliveryUrl")),
        "booking_url": _normalize_url(item.get("BookingUrl")),
        "detail_url": _normalize_url(item.get("DetailUrl")),
        "branch_url": _normalize_url(item.get("BranchUrl")),
        "cuisines": cuisines,
        "categories": categories,
        "latitude": item.get("Latitude"),
        "longitude": item.get("Longitude"),
    }


def extract_restaurants(html_path: Path = DEFAULT_HTML_PATH, output_csv: Path = DEFAULT_CSV_PATH):
    """
    Đọc HTML trang kết quả Foody, trích xuất danh sách nhà hàng (bao gồm các chi nhánh)
    và lưu thành file CSV.
    """
    data = _parse_json_from_html(html_path)

    rows = []
    for item in data.get("searchItems", []):
        rows.append(_item_to_row(item))
        for sub_item in item.get("SubItems", []):
            rows.append(_item_to_row(sub_item, parent_branch=item.get("Name") or item.get("BranchName")))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Đã trích xuất {len(rows)} nhà hàng vào {output_csv}")
    return rows


if __name__ == "__main__":
    extract_restaurants()
