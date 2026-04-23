from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth
from bs4 import BeautifulSoup
import psycopg2
import time
import random
import os

DB_CONFIG = {
    "host" : "db",
    "port" : "5432",
    "database": "realestate_db",
    "user": "dev_user",
    "password": "dev_password"
}

LOCATIONS = [
    {"name": "Hà Nội", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-tp-ha-noi"},
    {"name": "TP.HCM", "url": "https://batdongsan.com.vn/ban-can-ho-chung-cu-tp-ho-chi-minh"},
    {"name": "Đà Nẵng", "url": "https://batdongsan.com.vn/nha-dat-ban-tp-da-nang"}
]

MAX_PAGES_PER_LOCATION = 5
DOMAIN = "https://batdongsan.com.vn"

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

def crawl_page(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(random.uniform(5, 8))
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        tags = soup.find_all('a', class_='js__product-link-for-product-id')
        if not tags:
            print(f"Khong tim thay link")

        links = []
        for tag in tags:
            path = tag.get('href')

            if path:
                # Chỉ lấy link thuộc domain batdongsan.com.vn
                if path.startswith("http") and DOMAIN not in path:
                    continue
                full_url = path if path.startswith("http") else DOMAIN + path
                links.append(full_url)
        return links
    except Exception as e:
        print(f"Loi khi cao {url}: {e}")
        return []

def crawl_link():
    with Stealth().use_sync(sync_playwright()) as p:
        user_data_dir = os.path.join(os.getcwd(), "playwright_data")
        context = p.chromium.launch_persistent_context(user_data_dir, headless=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        args=["--disable-blink-features=AutomationControlled"])
        page = context.pages[0] if context.pages else context.new_page()

        total_new_links = 0
        for loc in LOCATIONS:
            print(f"Dang cao tai: {loc['name']}")
            for i in range(1, MAX_PAGES_PER_LOCATION+1):
                cur_url=f"{loc['url']}/p{i}" if i>1 else loc['url']
                print(f"Trang {i}:{cur_url}")
                links = crawl_page(page, cur_url)
                if links:
                    new_count = save_to_db(links)
                    total_new_links += new_count
                    print(f"Tim thay {len(links)} tin. Luu moi: {new_count}")
                    wait_time = random.uniform(5, 10)
                    time.sleep(wait_time)
        print(f"\n Tong cong them {total_new_links} vao database")
        context.close()        

if __name__ == "__main__":
    crawl_link()