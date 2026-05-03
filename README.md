# Wholesale PO Processing Pipeline

> **Disclaimer:** This project uses fictional purchase order data for demonstration
> purposes only. Retailer names (JCPenney, DSW, Famous Footwear) are used as realistic
> stand-ins and are not affiliated with or endorsing this project.

## Project Description

This pipeline automates purchase order processing for Evolution Design Lab, a wholesale footwear company supplying JCPenney, Famous Footwear, and DSW. When a retailer submits a PO (as a CSV or PDF), the system parses the line items, validates each one against live inventory, and uses the Claude AI API to generate plain-English exception summaries, recommended actions, and a ready-to-send buyer email — all in seconds, with no manual review required for clean orders.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                         │
│           CSV File  ──────┐   PDF File                     │
│                           ▼                                │
│                 POST /upload-po (FastAPI)                   │
└───────────────────────────┬────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │     pipeline/ingest.py    │
              │   parse_csv / parse_pdf   │
              │     → PODocument          │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │    pipeline/validate.py   │
              │  Query SQLite inventory   │
              │  Check: SKU, stock,       │
              │  price tolerance, max qty │
              │     → ValidationReport    │
              └──────┬──────────┬─────────┘
                     │          │
               passed > 0    flagged > 0
                     │          │
                     │  ┌───────▼──────────────┐
                     │  │ pipeline/exceptions.py│
                     │  │  Claude API call      │
                     │  │  → ExceptionSummary   │
                     │  └───────┬──────────────┘
                     │          │
              ┌──────▼──────────▼──────────┐
              │     db/database.py         │
              │  Store in processed_pos    │
              │  (SQLite)                  │
              └────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │    JSON Response to        │
              │  API caller / n8n node     │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │       n8n Workflow         │
              │  IF flagged → Gmail email  │
              │  ELSE       → Slack #ops   │
              └────────────────────────────┘
```

---

## Setup

```bash
# 1. Clone and install
git clone <repo-url>
cd po-pipeline
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and set your Anthropic API key:
#   ANTHROPIC_API_KEY=sk-ant-...

# 3. Initialise and seed the database
python -c "from db.database import init_db; init_db()"

# 4. Generate the sample PDF
python data/generate_pdf.py

# 5. Start the API
uvicorn api.main:app --reload --port 8000
```

---

## API Endpoints

### Health check
```bash
curl http://localhost:8000/health
```
```json
{"status": "ok"}
```

### Upload a PO (CSV or PDF)
```bash
curl -X POST http://localhost:8000/upload-po \
  -F "file=@data/sample_po.csv"
```

### Retrieve a validation report
```bash
curl http://localhost:8000/report/PO-JCP-2026-0412
```

### Retrieve exception summary
```bash
curl http://localhost:8000/exceptions/PO-JCP-2026-0412
```

---

## Sample Output

### POST /upload-po
```json
{
  "po_number": "PO-JCP-2026-0412",
  "status": "flagged",
  "validation_report": {
    "po_number": "PO-JCP-2026-0412",
    "validated_at": "2026-05-03T12:00:00",
    "total_lines": 12,
    "passed": 4,
    "flagged": 8,
    "line_results": [
      {
        "line_item": {"sku": "EDL-W-PUMP-BLK-7", "quantity": 60, "unit_price": 28.50, "...": "..."},
        "status": "ok",
        "available_stock": 120,
        "expected_price": 28.50,
        "notes": "All checks passed."
      },
      {
        "line_item": {"sku": "EDL-W-SANDAL-WHT-7", "quantity": 80, "...": "..."},
        "status": "stockout",
        "available_stock": 0,
        "expected_price": 22.00,
        "notes": "Insufficient stock: 0 units available, 80 requested."
      }
    ]
  },
  "exception_summary": {
    "po_number": "PO-JCP-2026-0412",
    "generated_at": "2026-05-03T12:00:05",
    "narrative": "PO-JCP-2026-0412 from JCPenney contains 8 flagged line items out of 12 total...",
    "recommended_actions": [
      "Contact JCPenney buyer to advise on stockout items EDL-W-SANDAL-WHT-7 and EDL-W-SNEAKER-BLK-6.",
      "Correct pricing discrepancies on EDL-W-PUMP-RED-6.5 and EDL-W-WEDGE-BGE-9 before confirming.",
      "Verify SKUs EDL-FAKE-SKU-001 and EDL-FAKE-SKU-002 with the buyer — these are not in inventory.",
      "Request revised quantities for EDL-W-BOOT-BLK-8 and EDL-W-FLAT-BLK-8 (exceed 200-unit limit)."
    ],
    "email_draft": "Dear JCPenney Buyer,\n\nThank you for submitting purchase order PO-JCP-2026-0412..."
  }
}
```

### GET /report/{po_number}
Returns the full `ValidationReport` JSON (same as `validation_report` above).

### GET /exceptions/{po_number}
Returns the full `ExceptionSummary` JSON, or `{"message": "no exceptions"}` if all lines passed.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use temporary SQLite databases via pytest fixtures. The Claude API is mocked
in `test_exceptions.py` so no tokens are consumed.

---

## n8n Workflow Setup

1. Open your n8n instance (self-hosted or cloud).
2. Go to **Workflows → Import** and upload `workflows/po_pipeline.json`.
3. Configure credentials:
   - **Gmail OAuth2**: Add a Google OAuth2 credential under *Settings → Credentials*.
   - **Slack API**: Add a Slack Bot Token credential.
4. Update the **Watch Incoming Folder** node path to your `incoming/` directory.
5. Activate the workflow. Drop any `.csv` or `.pdf` PO into `incoming/` to trigger it.

---

## API Documentation

FastAPI auto-generates interactive Swagger UI at:
```
http://localhost:8000/docs
```

---

## Technology Decisions

- **pypdf**: Pure-Python, zero system dependencies, handles the encrypted/compressed PDFs common in wholesale EDI.
- **SQLite**: No server process required; the entire inventory DB is a single file, ideal for a demo and easy to swap for Postgres in production.
- **FastAPI**: Async-native, generates OpenAPI docs automatically, and has first-class multipart file upload support.
- **Pydantic v2**: Provides runtime data validation and serialisation with zero extra code; models double as both input validators and JSON serialisers.
- **reportlab**: The de-facto Python library for programmatic PDF generation — no headless browser or external service required.
