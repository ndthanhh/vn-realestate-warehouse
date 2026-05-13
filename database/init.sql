CREATE TABLE IF NOT EXISTS raw_listings_links (
    url VARCHAR PRIMARY KEY,
    status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crawl_state (
    location_name VARCHAR PRIMARY KEY,
    current_page INT DEFAULT 1
);

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
