from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup
import psycopg2
import time
import random
import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

DB_CONFIG = {
    "host" : os.getenv("DB_HOST", "db"),
    "port" : os.getenv("DB_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "realestate_db"),
    "user": os.getenv("POSTGRES_USER", "dev_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "dev_password")
}

LOCATIONS = [
    {"name": "Hà Nội", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-ha-noi"},
    {"name": "TP.HCM", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-ho-chi-minh"},
    {"name": "Đà Nẵng", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-da-nang"},
    {"name": "Bình Dương", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-binh-duong"},
    {"name": "Đồng Nai", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-dong-nai"},
    {"name": "Hải Phòng", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-hai-phong"},
    {"name": "Quảng Ninh", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-quang-ninh"},
    {"name": "Khánh Hòa", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-khanh-hoa"},
    {"name": "Bà Rịa - Vũng Tàu", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-ba-ria-vung-tau"},
    {"name": "Bắc Ninh", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-bac-ninh"},
    {"name": "Hưng Yên", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-hung-yen"}
]

DOMAIN = "https://batdongsan.com.vn"

# === HÀM QUẢN LÝ TRẠNG THÁI ===

def get_current_page(location_name):
    """Lấy số trang đang cào dở của một tỉnh"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT current_page FROM crawl_state WHERE location_name = %s", (location_name,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 1
    except Exception as e:
        print(f"Loi lay state: {e}")
        return 1

def update_state(location_name, next_page):
    """Cập nhật trang tiếp theo cần cào"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = """
            INSERT INTO crawl_state (location_name, current_page)
            VALUES (%s, %s)
            ON CONFLICT (location_name) DO UPDATE SET current_page = EXCLUDED.current_page;
        """
        cur.execute(query, (location_name, next_page))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Loi luu state: {e}")

def get_next_location_index():
    """Lấy index tỉnh tiếp theo cần cào (xoay vòng round-robin)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT current_page FROM crawl_state WHERE location_name = '__next_index__'")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 0
    except Exception:
        return 0

def set_next_location_index(idx):
    """Lưu index tỉnh tiếp theo cho lần chạy sau"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crawl_state (location_name, current_page) VALUES ('__next_index__', %s)
            ON CONFLICT (location_name) DO UPDATE SET current_page = EXCLUDED.current_page
        """, (idx,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Loi luu index: {e}")

# === HÀM LƯU DỮ LIỆU ===

def save_to_db(links):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        insert_query = """
            INSERT INTO raw_listings_links (url)
            VALUES (%s)
            ON CONFLICT (url) DO NOTHING;
        """ 

        count = 0;
        for link in links:
            cur.execute(insert_query, (link,))
            if cur.rowcount > 0:
                count += 1

        conn.commit()
        print(f"Da luu {count} link vao database")
        cur.close()
        conn.close()
        return count

    except Exception as e:
        print(f"Loi: {e}")
        return 0

# === HÀM CÀO TRANG ===

def crawl_page(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Chờ cho đến khi JS render xong (tối đa 15s)
        try:
            page.wait_for_selector('a.js__product-link-for-product-id', state='attached', timeout=15000)
        except Exception:
            print("Khong the cho doi element js__product-link-for-product-id, co the bi Cloudflare hoac loi mang.")

        time.sleep(random.uniform(2, 4))
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        tags = soup.find_all('a', class_='js__product-link-for-product-id')
        if not tags:
            print(f"Khong tim thay link. Trang co the bi chan. Luu nguyen trang vao file html de debug...")
            slug = url.replace("https://", "").replace("/", "_").replace(".", "_")
            with open(f"/opt/crawler/debug_{slug}.html", "w", encoding="utf-8") as f:
                f.write(html)

        links = []
        for tag in tags:
            path = tag.get('href')

            if path:
                if path.startswith("http") and DOMAIN not in path:
                    continue
                full_url = path if path.startswith("http") else DOMAIN + path
                links.append(full_url)
        return links
    except Exception as e:
        print(f"Loi khi cao {url}: {e}")
        return []

# === HÀM CHÍNH ===

def crawl_link():
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "playwright_data")
        context = p.chromium.launch_persistent_context(user_data_dir, headless=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        args=["--disable-blink-features=AutomationControlled"])
        page = context.pages[0] if context.pages else context.new_page()

        stealth_sync(page)

        # Lấy tỉnh tiếp theo theo thứ tự xoay vòng (round-robin)
        loc_index = get_next_location_index()
        loc = LOCATIONS[loc_index % len(LOCATIONS)]
        current_page = get_current_page(loc['name'])

        print(f"[{loc['name']}] Dang cao trang: {current_page}")
        cur_url = f"{loc['url']}/p{current_page}" if current_page > 1 else loc['url']

        links = crawl_page(page, cur_url)

        if links:
            new_count = save_to_db(links)
            print(f"Tim thay {len(links)} tin. Luu moi: {new_count}")
            update_state(loc['name'], current_page + 1)
        else:
            print(f"Den trang cuoi cua {loc['name']}")
            update_state(loc['name'], 1)

        # Xoay sang tỉnh tiếp theo cho lần chạy sau
        next_index = (loc_index + 1) % len(LOCATIONS)
        set_next_location_index(next_index)
        print(f"Lan chay tiep theo se cao: {LOCATIONS[next_index]['name']}")

        context.close()

if __name__ == "__main__":
    crawl_link()