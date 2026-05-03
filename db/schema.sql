CREATE TABLE IF NOT EXISTS inventory (
    sku TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    color TEXT NOT NULL,
    size TEXT NOT NULL,
    stock_count INTEGER NOT NULL DEFAULT 0,
    wholesale_price REAL NOT NULL,
    category TEXT NOT NULL,
    max_order_qty INTEGER NOT NULL DEFAULT 200
);

CREATE TABLE IF NOT EXISTS processed_pos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number TEXT UNIQUE NOT NULL,
    retailer TEXT NOT NULL,
    submitted_date TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    validation_json TEXT,
    exception_json TEXT
);
