-- Shopify Inventory Control Tower — SQLite Schema

CREATE TABLE IF NOT EXISTS variants (
    id              TEXT PRIMARY KEY,
    product_id      TEXT NOT NULL,
    sku             TEXT,
    title           TEXT,
    product_title   TEXT,
    price           REAL,
    created_at      DATETIME,
    updated_at      DATETIME,
    synced_at       DATETIME
);

CREATE TABLE IF NOT EXISTS inventory_levels (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      TEXT NOT NULL,
    location_id     TEXT NOT NULL,
    location_name   TEXT,
    available       INTEGER DEFAULT 0,
    updated_at      DATETIME,
    synced_at       DATETIME,
    UNIQUE(variant_id, location_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id              TEXT PRIMARY KEY,
    order_number    TEXT,
    created_at      DATETIME,
    financial_status TEXT,
    total_price     REAL,
    synced_at       DATETIME
);

CREATE TABLE IF NOT EXISTS order_items (
    id              TEXT PRIMARY KEY,
    order_id        TEXT NOT NULL,
    variant_id      TEXT,
    sku             TEXT,
    title           TEXT,
    quantity        INTEGER DEFAULT 0,
    price           REAL,
    created_at      DATETIME
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type        TEXT,
    status          TEXT,
    records_synced  INTEGER DEFAULT 0,
    started_at      DATETIME,
    finished_at     DATETIME,
    notes           TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_variants_sku         ON variants(sku);
CREATE INDEX IF NOT EXISTS idx_variants_product_id  ON variants(product_id);
CREATE INDEX IF NOT EXISTS idx_inv_variant          ON inventory_levels(variant_id);
CREATE INDEX IF NOT EXISTS idx_order_items_variant  ON order_items(variant_id);
CREATE INDEX IF NOT EXISTS idx_order_items_sku      ON order_items(sku);
CREATE INDEX IF NOT EXISTS idx_orders_created       ON orders(created_at);
