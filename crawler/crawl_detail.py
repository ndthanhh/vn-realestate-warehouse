from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup
import psycopg2
import io
import random
import time
from minio import Minio
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

PG2_CONFIG={
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "realestate_db"),
    "user": os.getenv("POSTGRES_USER", "dev_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "dev_password")
}

MINIO_CONFIG={
    "endpoint": os.getenv("MINIO_ENDPOINT", "minio:9000"),
    "access_key": os.getenv("MINIO_ROOT_USER", "minioadmin"),
    "secret_key": os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
    "secure": False
}

BUCKET_NAME="realestate"

def load_from_pg2(limit = 10):
    try:
        conn = psycopg2.connect(**PG2_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT url FROM raw_listings_links WHERE status = 'pending' LIMIT %s", (limit,))
        links =[]
        rows = cur.fetchall()
        for row in rows:
            links.append(row[0])
        cur.close()
        conn.close()
        return links
    except Exception as e:
        print(f"Loi tai links: {e}")
        return []

def update_status_pg2(url):
    try:
        conn = psycopg2.connect(**PG2_CONFIG)   
        cur = conn.cursor()
        cur.execute("UPDATE raw_listings_links SET status = 'crawled' WHERE url = %s", (url,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Loi khi update links: {e}")

def upload_to_minio(client, data, url):
    slug = url.strip("/").split("/")[-1]
    file_name = f"{slug}.json"
    date_str = datetime.now().strftime("%Y-%m-%d")
    object_name = f"bronze/batdongsan/dt={date_str}/{file_name}"

    json_data =json.dumps(data, ensure_ascii=False).encode('utf-8')
    try:
        client.put_object(
            BUCKET_NAME,
            object_name,
            data=io.BytesIO(json_data),
            length=len(json_data),
            content_type='application/json'
        )
        print(f"Da tai len MinIO: {object_name}")
        return True
    except Exception as e:
        print(f"Loi tai len MinIO: {e}")
        return False

def scrape_detail(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    
    try:
        page.wait_for_selector('h1.re__pr-title', state='attached', timeout=30000)
    except Exception:
        raise Exception("Bi Cloudflare chan hoac trang khong co du lieu, DUNG LUU vao MinIO!")
    
    time.sleep(random.uniform(3, 5))
    page.evaluate("scrollBy(0, 800)")
    time.sleep(2)

    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

    title_tag = soup.find('h1', class_='re__pr-title')
    title = title_tag.get_text(strip=True) if title_tag else ""

    addr_line_1 = soup.find('span', class_='re__address-line-1')
    addr_line_2 = soup.find('span', class_='re__address-line-2')
    
    address_1 = addr_line_1.get_text(strip=True) if addr_line_1 else ""
    address_2 = addr_line_2.get_text(strip=True).strip("()") if addr_line_2 else ""

    short_info={}
    items = soup.find_all('div', class_='re__pr-short-info-item')
    for item in items:
        label = item.find('span', class_='title')
        value = item.find('span', class_='value')
        ext = item.find('span', class_='ext')

        if label and value:
            key = label.get_text(strip=True)
            short_info[key] = value.get_text(strip=True)
            if ext:
                short_info[key+"(ext)"] = ext.get_text(strip=True)

    specs={}
    items1 = soup.find_all('div', class_="re__pr-specs-content-item")
    for item in items1:
        label = item.find('span', class_='re__pr-specs-content-item-title')
        value = item.find('span', class_='re__pr-specs-content-item-value')

        if label and value:
            key = label.get_text(strip=True)
            specs[key] = value.get_text(strip=True)

    desc_tag = soup.find('div',class_='re__detail-content')
    description =desc_tag.get_text(separator="\n", strip=True) if desc_tag else ""

    return {
        "url": url,
        "title": title,
        "address": address_1,
        "address_line_2": address_2,
        "short_info": short_info,
        "specs": specs,
        "description": description,
        "crawled_at": datetime.now().isoformat()
    }


def run():
    minio_client=Minio(**MINIO_CONFIG)
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)

    links = load_from_pg2(limit=1)
    if not links:
        print("Khong con links nao!")
        return 

    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "playwright_data_detail")
        context=p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        stealth_sync(page)

        for url in links:
            print(f"Dang cao: {url}")
            try:
                data=scrape_detail(page, url)
                success = upload_to_minio(minio_client, data, url)
                if success:
                    update_status_pg2(url)
            except Exception as e:
                print(f"Loi cao: {e}")

            wait_time = random.uniform(20, 35)
            print(f"Nghi ngoi {wait_time:.1f} giay de ne Cloudflare...")
            time.sleep(wait_time)
        
        context.close()
    print("Done!")

if __name__ == "__main__":
    run()