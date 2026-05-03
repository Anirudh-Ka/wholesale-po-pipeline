-- Inventory seed data for Evolution Design Lab wholesale footwear
-- Format: EDL-{gender}-{style}-{color}-{size}
-- Genders: W (women), M (men), U (unisex)
-- Colors: BLK, TAN, NAV, RED, WHT, BGE
-- Sizes: 6, 6.5, 7, 7.5, 8, 8.5, 9, 10

INSERT OR IGNORE INTO inventory (sku, description, color, size, stock_count, wholesale_price, category) VALUES
-- PUMPs (healthy stock)
('EDL-W-PUMP-BLK-7',   'Women''s Classic Pump Black Size 7',   'BLK', '7',   120, 28.50, 'PUMP'),
('EDL-W-PUMP-BLK-7.5', 'Women''s Classic Pump Black Size 7.5', 'BLK', '7.5', 95,  28.50, 'PUMP'),
('EDL-W-PUMP-NAV-8',   'Women''s Classic Pump Navy Size 8',    'NAV', '8',   80,  28.50, 'PUMP'),
('EDL-W-PUMP-RED-6.5', 'Women''s Classic Pump Red Size 6.5',   'RED', '6.5', 10,  28.50, 'PUMP'),

-- SANDALs (mixed stock)
('EDL-W-SANDAL-TAN-8',   'Women''s Strappy Sandal Tan Size 8',   'TAN', '8',   150, 22.00, 'SANDAL'),
('EDL-W-SANDAL-TAN-8.5', 'Women''s Strappy Sandal Tan Size 8.5', 'TAN', '8.5', 60,  22.00, 'SANDAL'),
('EDL-W-SANDAL-WHT-7',   'Women''s Strappy Sandal White Size 7', 'WHT', '7',   0,   22.00, 'SANDAL'),  -- OUT OF STOCK
('EDL-W-SANDAL-BGE-9',   'Women''s Strappy Sandal Beige Size 9', 'BGE', '9',   5,   22.00, 'SANDAL'),

-- BOOTs (healthy stock)
('EDL-W-BOOT-BLK-7',   'Women''s Ankle Boot Black Size 7',   'BLK', '7',   200, 42.00, 'BOOT'),
('EDL-W-BOOT-BLK-8',   'Women''s Ankle Boot Black Size 8',   'BLK', '8',   175, 42.00, 'BOOT'),
('EDL-W-BOOT-TAN-7.5', 'Women''s Ankle Boot Tan Size 7.5',   'TAN', '7.5', 90,  42.00, 'BOOT'),
('EDL-W-BOOT-NAV-9',   'Women''s Ankle Boot Navy Size 9',    'NAV', '9',   30,  42.00, 'BOOT'),

-- SNEAKERs
('EDL-W-SNEAKER-WHT-7',  'Women''s Canvas Sneaker White Size 7',  'WHT', '7',  110, 18.50, 'SNEAKER'),
('EDL-W-SNEAKER-WHT-8',  'Women''s Canvas Sneaker White Size 8',  'WHT', '8',  85,  18.50, 'SNEAKER'),
('EDL-W-SNEAKER-BLK-6',  'Women''s Canvas Sneaker Black Size 6',  'BLK', '6',  0,   18.50, 'SNEAKER'),  -- OUT OF STOCK
('EDL-W-SNEAKER-RED-7.5','Women''s Canvas Sneaker Red Size 7.5',  'RED', '7.5',45,  18.50, 'SNEAKER'),

-- FLATs
('EDL-W-FLAT-BGE-7',  'Women''s Ballet Flat Beige Size 7',  'BGE', '7',  130, 20.00, 'FLAT'),
('EDL-W-FLAT-BLK-8',  'Women''s Ballet Flat Black Size 8',  'BLK', '8',  100, 20.00, 'FLAT'),
('EDL-W-FLAT-TAN-6.5','Women''s Ballet Flat Tan Size 6.5',  'TAN', '6.5',55,  20.00, 'FLAT'),

-- WEDGEs
('EDL-W-WEDGE-TAN-8',  'Women''s Espadrille Wedge Tan Size 8',  'TAN', '8',  70,  32.00, 'WEDGE'),
('EDL-W-WEDGE-WHT-7.5','Women''s Espadrille Wedge White Size 7.5','WHT','7.5',40, 32.00, 'WEDGE'),
('EDL-W-WEDGE-BGE-9',  'Women''s Espadrille Wedge Beige Size 9', 'BGE', '9',  15,  32.00, 'WEDGE');

-- Lower allocation caps on two SKUs to enable QUANTITY_EXCEEDED demo in sample_po
-- (stock is sufficient, but retailer cap is intentionally restrictive)
UPDATE inventory SET max_order_qty = 100 WHERE sku = 'EDL-W-BOOT-BLK-8';
UPDATE inventory SET max_order_qty = 80  WHERE sku = 'EDL-W-FLAT-BLK-8';
