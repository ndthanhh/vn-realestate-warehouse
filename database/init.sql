-- =============================================
-- VN Realestate Warehouse - Database Schema
-- File này tự động chạy khi Postgres khởi tạo lần đầu
-- =============================================

-- Bảng lưu trữ các URL đã thu thập được
CREATE TABLE IF NOT EXISTS raw_listings_links (
    url VARCHAR PRIMARY KEY,
    status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bảng lưu trạng thái cào (trang hiện tại) của từng tỉnh
CREATE TABLE IF NOT EXISTS crawl_state (
    location_name VARCHAR PRIMARY KEY,
    current_page INT DEFAULT 1
);

-- Bảng Gold Layer - Dữ liệu sạch phục vụ Dashboard
CREATE TABLE IF NOT EXISTS fact_listings (
    url VARCHAR PRIMARY KEY,
    project_name VARCHAR,
    title VARCHAR,
    district VARCHAR,
    city VARCHAR,
    price DOUBLE PRECISION,
    area_m2 DOUBLE PRECISION,
    price_per_m2 DOUBLE PRECISION,
    num_bedrooms INT,
    house_direction VARCHAR,
    has_legal_docs INT,
    posted_date DATE,
    dt DATE,
    gold_loaded_at TIMESTAMP
);
