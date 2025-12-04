from pathlib import Path

from playwright.sync_api import sync_playwright


def dump_html(city="da-nang", category="nha-hang", page=1, output_dir="data"):
    """
    Tải HTML của 1 trang kết quả Foody và lưu vào thư mục output_dir.
    Trả về đường dẫn file đã lưu.
    """
    base_url = f"https://www.foody.vn/{city}/{category}?page={page}"
    output_path = Path(output_dir) / f"foody_page{page}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        # headless=True cho chạy tự động, đổi thành False nếu cần quan sát
        browser = pw.chromium.launch(headless=True)
        page_obj = browser.new_page()

        print("Visiting:", base_url)
        page_obj.goto(base_url, timeout=60000)

        # chờ JS render xong
        page_obj.wait_for_timeout(5000)

        html = page_obj.content()
        output_path.write_text(html, encoding="utf-8")

        print("Saved HTML to", output_path)
        browser.close()

    return output_path


if __name__ == "__main__":
    dump_html()
