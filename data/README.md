# Mock Data

## inventory_seed.sql

Seeds 22 footwear SKUs for Evolution Design Lab. SKU format: `EDL-{gender}-{style}-{color}-{size}`.

- **Styles:** PUMP, SANDAL, BOOT, SNEAKER, FLAT, WEDGE
- **Colors:** BLK, TAN, NAV, RED, WHT, BGE
- **Sizes:** 6 – 10
- **Wholesale price range:** $18.50 – $42.00
- Two SKUs have reduced `max_order_qty` to enable the QUANTITY_EXCEEDED demo:
  - `EDL-W-BOOT-BLK-8`: max_order_qty=100 (stock=175)
  - `EDL-W-FLAT-BLK-8`: max_order_qty=80 (stock=100)

## sample_po.csv / sample_po.pdf

PO `PO-JCP-2026-0412` for JCPenney with 12 line items demonstrating all exception types:

| Lines | Count | Expected outcome |
|-------|-------|-----------------|
| 1–4   | 4     | OK — price and stock match |
| 5–6   | 2     | STOCKOUT — items with stock_count=0 |
| 7–8   | 2     | PRICE_MISMATCH — PO price differs >5% from wholesale |
| 9–10  | 2     | INVALID_SKU — SKUs not in inventory |
| 11–12 | 2     | QUANTITY_EXCEEDED — qty exceeds max_order_qty but stock is available |

To regenerate the PDF after editing the CSV:
```bash
python data/generate_pdf.py
```
