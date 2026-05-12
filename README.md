# 🏠 Vietnam Real Estate Data Warehouse

An end-to-end data engineering pipeline that **crawls**, **processes**, **stores**, and **visualizes** apartment listing data from [batdongsan.com.vn](https://batdongsan.com.vn) — Vietnam's largest real estate marketplace.

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Apache Airflow (Orchestration)               │
│                                                                  │
│   dag_crawl_links (15min)  dag_crawl_details (5min)  dag_etl    │
└────────┬───────────────────────────┬────────────────────┬────────┘
         │                           │                    │
         ▼                           ▼                    ▼
┌─────────────────┐   ┌─────────────────────┐   ┌───────────────┐
│  Listing Crawler │   │  Detail Crawler      │   │  Spark ETL    │
│  (Playwright)    │   │  (Playwright)        │   │  (PySpark)    │
│                  │   │                      │   │               │
│  Crawl URLs from │   │  Scrape detail info  │   │  Bronze → Silver │
│  listing pages   │   │  from each listing   │   │  Silver → Gold   │
└───────┬──────────┘   └──────────┬───────────┘   └───┬───────┬───┘
        │                         │                   │       │
        ▼                         ▼                   │       ▼
┌──────────────┐          ┌──────────────┐            │  ┌──────────┐
│  PostgreSQL  │          │  MinIO (S3)  │────────────┘  │PostgreSQL│
│  (URL Queue) │          │  Bronze JSON │               │  (Gold)  │
└──────────────┘          │  Silver Parquet│              └────┬─────┘
                          └──────────────┘                    │
                                                              ▼
                                                     ┌───────────────┐
                                                     │   Streamlit   │
                                                     │   Dashboard   │
                                                     └───────────────┘
```

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Crawling** | Playwright + BeautifulSoup | Web scraping with anti-bot evasion |
| **Storage (Bronze)** | MinIO (S3-compatible) | Raw JSON data lake |
| **Processing** | Apache Spark (PySpark) | ETL: cleaning, transforming, deduplication |
| **Storage (Silver)** | MinIO (Parquet) | Cleaned & structured data |
| **Storage (Gold)** | PostgreSQL | Analytics-ready fact table |
| **Orchestration** | Apache Airflow | DAG scheduling & monitoring |
| **Visualization** | Streamlit + Plotly | Interactive dashboard |
| **Infrastructure** | Docker Compose | Container orchestration |

## 📂 Project Structure

```
vn-realestate-warehouse/
├── airflow/
│   └── dags/
│       ├── dag_crawl_links.py      # Crawl listing URLs (every 15 min)
│       ├── dag_crawl_details.py     # Scrape detail pages (every 5 min)
│       └── dag_etl.py               # Spark ETL pipeline (daily at 2 AM)
├── crawler/
│   ├── crawl_link.py                # Listing page crawler (round-robin by province)
│   └── crawl_detail.py              # Detail page scraper → MinIO Bronze
├── spark_jobs/
│   ├── etl_bronze_to_sliver.py      # Bronze (JSON) → Silver (Parquet)
│   └── etl_silver_to_gold.py        # Silver (Parquet) → Gold (PostgreSQL)
├── dashboard/
│   ├── app.py                       # Streamlit dashboard
│   ├── Dockerfile                   # Dashboard container
│   └── requirements.txt
├── database/
│   └── init.sql                     # PostgreSQL schema (auto-init)
├── docker-compose.yaml              # Full infrastructure stack
├── Dockerfile.airflow               # Custom Airflow image with Playwright
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for local development)

### 1. Clone & Configure

```bash
git clone https://github.com/<your-username>/vn-realestate-warehouse.git
cd vn-realestate-warehouse
cp .env.example .env
```

### 2. Start Infrastructure

```bash
docker compose up -d
```

This launches:
- **PostgreSQL** (port `5439`) — Main database
- **MinIO** (port `9000`, console `9001`) — S3-compatible object storage
- **Spark Master** (port `8080`) + Worker — Distributed processing
- **Airflow Webserver** (port `8081`) + Scheduler — Workflow orchestration

### 3. Verify Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow UI | http://localhost:8081 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| Spark Master UI | http://localhost:8080 | — |

### 4. Run Dashboard Locally

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Dashboard will be available at http://localhost:8501

## 📊 Dashboard Features

The interactive dashboard provides:

- **KPI Metrics** — Total listings, average price, average area, legal document count
- **Price by Ward/Commune** — Bar chart of average price per administrative ward
- **Area vs Price Correlation** — Scatter plot with city-based color coding
- **Unit Price Analysis** — Average price per m² by location (Triệu/m²)
- **Legal Status Distribution** — Pie chart of legal document availability
- **Price Distribution** — Box plot (multi-city) or histogram (single city)
- **Data Table** — Searchable, filterable raw data explorer

**Sidebar Filters:** City, Price Range, Price per m², Number of Bedrooms

## 🔄 Data Pipeline Details

### Medallion Architecture

| Layer | Format | Storage | Description |
|-------|--------|---------|-------------|
| **Bronze** | JSON | MinIO `s3://realestate/bronze/` | Raw scraped data, partitioned by crawl date |
| **Silver** | Parquet | MinIO `s3://realestate/silver/` | Cleaned, typed, filtered data |
| **Gold** | Relational | PostgreSQL `fact_listings` | Deduplicated, enriched, dashboard-ready |

### ETL Transformations (Bronze → Silver)
- Null/empty title filtering (Cloudflare-blocked pages)
- Address parsing from `address_line_2` (post-merger administrative data)
- Administrative unit filtering (only Xã/Phường level)
- Price, area, price/m² extraction and type casting
- Date parsing (posted_date, crawled_at)

### ETL Transformations (Silver → Gold)
- URL-based deduplication
- Legal status flag derivation (has_legal_docs)
- Bedroom count extraction from specs
- Project name extraction using regex-based filtering
- UPSERT into PostgreSQL via staging table pattern

## ⚙️ Configuration

All credentials are configurable via environment variables. See [`.env.example`](.env.example) for the full list.

## 📝 License

This project is for educational and portfolio purposes.