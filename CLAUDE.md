# Wholesale Order Processing Pipeline — Claude Code Context

## Who You Are Building This For

This project is being built by Anirudh Katupilla (Ani), an M.S. Applied Machine Learning
student at University of Maryland (GPA 3.8), specializing in reinforcement learning and
Bayesian inference. He is applying for an AI/automation internship at Evolution Design Lab,
a women's wholesale footwear company that sells to JCPenney, Famous Footwear, and DSW.

The project must be polished, functional, and directly demonstrable. Every component must
actually run. No placeholder logic, no fake stubs. If you are unsure how to implement
something, implement the simplest real version rather than mocking it.

---

## Project Goal

Build an end-to-end AI-powered wholesale purchase order (PO) processing pipeline that:

1. Accepts a retailer PO as PDF or CSV
2. Extracts structured line items (SKU, quantity, price, retailer name, delivery date)
3. Validates each line item against a mock inventory database
4. Flags exceptions (stockouts, price mismatches, invalid SKUs, quantity overruns)
5. Uses the Anthropic Claude API to generate plain-English exception summaries and
   recommended actions
6. Exposes everything via a FastAPI REST interface
7. Wraps the full workflow in an n8n-compatible JSON workflow definition

This maps directly to real operations at a wholesale footwear company. The mock data
should reflect realistic footwear SKUs, sizes, colors, and retailer names.

---

## Tech Stack

- **Language:** Python 3.11+
- **PDF parsing:** pypdf
- **Data validation:** Pydantic v2
- **Database:** SQLite via sqlite3 (no ORM, raw SQL is fine)
- **API:** FastAPI + uvicorn
- **Claude integration:** anthropic Python SDK (use claude-sonnet-4-6)
- **Workflow:** n8n workflow JSON (exported format, importable into n8n)
- **Testing:** pytest with at least one test per module
- **Dependency management:** requirements.txt

Do NOT use LangChain, LlamaIndex, or any agent framework. Keep dependencies minimal.

---

## Project File Structure

Build exactly this structure:

```
po-pipeline/
├── CLAUDE.md                  # This file (copy here too)
├── README.md                  # Setup, architecture, sample run
├── requirements.txt
├── .env.example               # ANTHROPIC_API_KEY=your_key_here
│
├── data/
│   ├── sample_po.csv          # Mock PO with 10-15 line items
│   ├── sample_po.pdf          # Same PO as PDF (generate programmatically)
│   └── inventory_seed.sql     # SQL to seed the inventory database
│
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py              # PDF + CSV parsing, outputs PODocument (Pydantic)
│   ├── validate.py            # Inventory validation, outputs ValidationReport
│   ├── exceptions.py          # Claude API calls, generates exception summaries
│   └── models.py              # All Pydantic models used across the pipeline
│
├── db/
│   ├── __init__.py
│   ├── schema.sql             # CREATE TABLE statements
│   └── database.py            # SQLite connection, query helpers
│
├── api/
│   ├── __init__.py
│   └── main.py                # FastAPI app, three endpoints
│
├── workflows/
│   └── po_pipeline.json       # n8n workflow JSON
│
└── tests/
    ├── test_ingest.py
    ├── test_validate.py
    └── test_exceptions.py
```

---

## Pydantic Models (define in pipeline/models.py)

```python
class LineItem(BaseModel):
    sku: str
    description: str
    retailer: str
    quantity: int
    unit_price: float
    requested_delivery: date

class PODocument(BaseModel):
    po_number: str
    retailer: str
    submitted_date: date
    line_items: list[LineItem]

class ValidationStatus(str, Enum):
    OK = "ok"
    STOCKOUT = "stockout"
    PRICE_MISMATCH = "price_mismatch"
    INVALID_SKU = "invalid_sku"
    QUANTITY_EXCEEDED = "quantity_exceeded"

class LineValidation(BaseModel):
    line_item: LineItem
    status: ValidationStatus
    available_stock: int | None
    expected_price: float | None
    notes: str

class ValidationReport(BaseModel):
    po_number: str
    validated_at: datetime
    total_lines: int
    passed: int
    flagged: int
    line_results: list[LineValidation]

class ExceptionSummary(BaseModel):
    po_number: str
    generated_at: datetime
    narrative: str          # Claude-generated plain English summary
    recommended_actions: list[str]   # Claude-generated action items
    email_draft: str        # Ready-to-send email draft for the buyer
```

---

## Database Schema (db/schema.sql)

```sql
CREATE TABLE IF NOT EXISTS inventory (
    sku TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    color TEXT NOT NULL,
    size TEXT NOT NULL,
    stock_count INTEGER NOT NULL DEFAULT 0,
    wholesale_price REAL NOT NULL,
    category TEXT NOT NULL
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
```

---

## Mock Data Requirements

### Sample PO (data/sample_po.csv)

Generate a realistic CSV with 12 line items for retailer "JCPenney". Include:
- 4 items that pass validation cleanly
- 2 items with stockout (quantity requested exceeds stock)
- 2 items with price mismatch (PO price differs from wholesale price by more than 5%)
- 2 items with invalid SKU (not in inventory)
- 2 items with quantity exceeded (over retailer's max order qty)

Use realistic footwear SKUs like: `EDL-W-PUMP-BLK-7`, `EDL-W-SANDAL-TAN-8`, etc.
Format: `EDL-{gender}-{style}-{color}-{size}`

### Inventory Seed (data/inventory_seed.sql)

Seed at least 20 SKUs across styles: PUMP, SANDAL, BOOT, SNEAKER, FLAT, WEDGE.
Colors: BLK (black), TAN, NAV (navy), RED, WHT (white), BGE (beige).
Sizes: 6, 6.5, 7, 7.5, 8, 8.5, 9, 10.
Wholesale prices: $18-$45 range.
Stock counts: mix of 0 (out of stock), low (1-20), and healthy (50-200).

---

## Module Implementation Details

### pipeline/ingest.py

- `parse_csv(file_path: str) -> PODocument`
- `parse_pdf(file_path: str) -> PODocument`
  - For PDF: extract text with pypdf, then parse with regex or structured extraction
  - Both functions must return the same PODocument schema
- Handle malformed rows gracefully, log warnings, skip bad lines

### pipeline/validate.py

- `validate_po(po: PODocument, db_path: str) -> ValidationReport`
- For each line item, query inventory table for SKU
- Check: SKU exists, stock >= quantity, price within 5% tolerance
- Return full ValidationReport with per-line status

### pipeline/exceptions.py

- `generate_exception_summary(report: ValidationReport) -> ExceptionSummary`
- Only call Claude API if report.flagged > 0
- System prompt: you are an operations assistant for a wholesale footwear company
- Pass the flagged line items as structured context
- Ask Claude to: summarize exceptions in plain English, list recommended actions,
  draft a professional email to the buyer explaining the issues
- Use claude-sonnet-4-6, max_tokens=1000
- Load ANTHROPIC_API_KEY from environment via python-dotenv

### api/main.py

Three endpoints:

```
POST /upload-po
  - Accepts multipart file upload (CSV or PDF)
  - Runs full pipeline: ingest -> validate -> exceptions (if needed)
  - Stores result in processed_pos table
  - Returns: { po_number, status, validation_report, exception_summary }

GET /report/{po_number}
  - Returns stored ValidationReport for a given PO number
  - 404 if not found

GET /exceptions/{po_number}
  - Returns stored ExceptionSummary for a given PO number
  - Returns { message: "no exceptions" } if all lines passed
```

---

## n8n Workflow (workflows/po_pipeline.json)

Generate a valid n8n workflow JSON with these nodes:

1. **Trigger:** Watch Folder node (watches a local `incoming/` directory)
2. **HTTP Request:** POST to `http://localhost:8000/upload-po` with the file
3. **IF node:** Check if `flagged > 0` in response
4. **Gmail node (true branch):** Send exception summary email (use placeholder credentials)
5. **Slack node (false branch):** Post success message to #ops channel
6. **Set node:** Log result to a local JSON file

The workflow JSON must be valid and importable into n8n v1.x.

---

## README.md Requirements

Write a README that includes:

1. **One-paragraph project description** (written for a non-technical hiring manager)
2. **Architecture diagram** (ASCII is fine, show data flow from PO input to output)
3. **Setup instructions** (clone, pip install, seed DB, set env var, run uvicorn)
4. **Sample run** with curl commands for each endpoint
5. **Sample output** (paste a realistic JSON response for each endpoint)
6. **n8n setup** (how to import the workflow and configure credentials)
7. **Tech decisions** (one sentence each on why pypdf, SQLite, FastAPI, Pydantic)

---

## Quality Requirements

- All code must be PEP 8 compliant
- Every function must have a docstring
- Use type hints everywhere
- No hardcoded paths, use pathlib.Path
- Environment variables loaded via python-dotenv, never hardcoded
- All file I/O wrapped in try/except with meaningful error messages
- The FastAPI app must include CORS middleware and a /health endpoint
- Tests must use pytest fixtures, not hardcoded file paths

---

## How to Run This Project (for Ani to verify in the morning)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 3. Initialize and seed database
python -c "from db.database import init_db; init_db()"

# 4. Run the API
uvicorn api.main:app --reload --port 8000

# 5. Test with sample PO
curl -X POST http://localhost:8000/upload-po \
  -F "file=@data/sample_po.csv"

# 6. Run tests
pytest tests/ -v
```

---

## Instance Assignments

There are 3 Claude Code instances running in parallel overnight. Each instance has a
specific scope. Do not touch files outside your assigned scope. If you need something
from another instance's scope, read it but do not modify it.

---

### INSTANCE 1: Foundation (Start First, Others Depend On You)

You are Instance 1. Your job is the shared foundation that the other two instances
build on top of. You must finish pipeline/models.py and db/ before the others can
start meaningfully. Work fast on those first, then move to data generation.

**Your files:**
- `pipeline/__init__.py`
- `pipeline/models.py` — ALL Pydantic models used across the entire project
- `db/__init__.py`
- `db/schema.sql`
- `db/database.py`
- `data/inventory_seed.sql`
- `data/sample_po.csv`
- `data/sample_po.pdf`
- `requirements.txt`
- `.env.example`

**Your order of operations:**
1. Create the full project directory structure (all folders and empty `__init__.py` files)
2. Write `requirements.txt` with all dependencies
3. Write `pipeline/models.py` — this is the most critical file, get it right
4. Write `db/schema.sql` and `db/database.py`
5. Write `data/inventory_seed.sql` with 20+ realistic footwear SKUs
6. Generate `data/sample_po.csv` with 12 line items (4 clean, 2 stockout, 2 price
   mismatch, 2 invalid SKU, 2 quantity exceeded)
7. Generate `data/sample_po.pdf` programmatically using reportlab (add to requirements)
8. Run `python -c "from db.database import init_db; init_db()"` and confirm it works
9. Write a short `data/README.md` explaining the mock data structure

**Your final check:**
- [ ] `python -c "from pipeline.models import PODocument; print('models ok')"` passes
- [ ] `python -c "from db.database import init_db; init_db()"` runs without errors
- [ ] `data/sample_po.csv` has exactly 12 rows with the right exception distribution
- [ ] `data/sample_po.pdf` opens and is readable

---

### INSTANCE 2: Pipeline Core (Start 15 Minutes After Instance 1)

You are Instance 2. Your job is the processing logic: ingestion, validation, and
Claude API integration. Wait until pipeline/models.py and db/database.py exist before
starting. If they don't exist yet, wait 5 minutes and check again.

**Your files:**
- `pipeline/ingest.py`
- `pipeline/validate.py`
- `pipeline/exceptions.py`
- `tests/__init__.py`
- `tests/test_ingest.py`
- `tests/test_validate.py`
- `tests/test_exceptions.py`

**Your order of operations:**
1. Read `pipeline/models.py` fully before writing anything
2. Read `db/database.py` fully before writing anything
3. Write `pipeline/ingest.py` — CSV parser first, then PDF parser
4. Test ingest against `data/sample_po.csv` immediately after writing it
5. Write `pipeline/validate.py` — query SQLite, check all 4 exception types
6. Test validate against the ingested PO, confirm it catches all flagged lines
7. Write `pipeline/exceptions.py` — Claude API call, generate ExceptionSummary
8. Test exceptions with a mock ValidationReport that has 3 flagged lines
9. Write `tests/test_ingest.py`, `tests/test_validate.py`, `tests/test_exceptions.py`
10. Run `pytest tests/ -v` and fix all failures

**Critical notes:**
- Import models only from `pipeline.models`, never redefine them
- For `test_exceptions.py`, mock the Anthropic API call with pytest monkeypatch so
  tests don't consume real API tokens
- The validate module must handle the case where inventory.db doesn't exist yet
  and raise a clear error message
- Load `ANTHROPIC_API_KEY` from `.env` using python-dotenv

**Your final check:**
- [ ] `python -c "from pipeline.ingest import parse_csv; print(parse_csv('data/sample_po.csv'))"` returns a PODocument
- [ ] `pytest tests/test_ingest.py -v` all pass
- [ ] `pytest tests/test_validate.py -v` all pass
- [ ] `pytest tests/test_exceptions.py -v` all pass (with mocked API)

---

### INSTANCE 3: API and Wrapper (Start 15 Minutes After Instance 1)

You are Instance 3. Your job is the FastAPI layer, the n8n workflow, and the README.
You can start writing api/main.py structure as soon as models.py exists, even if the
pipeline modules aren't done yet. Use try/except imports to handle partial availability.

**Your files:**
- `api/__init__.py`
- `api/main.py`
- `workflows/po_pipeline.json`
- `README.md`

**Your order of operations:**
1. Read `pipeline/models.py` fully before writing anything
2. Write `api/main.py` with all three endpoints and a /health endpoint
3. Add CORS middleware, proper HTTP exception handling, and request logging
4. Write the file upload handler that accepts both CSV and PDF via multipart
5. Wire up the full pipeline: ingest -> validate -> exceptions inside the POST endpoint
6. Add SQLite persistence: store results in `processed_pos` table after each run
7. Test all endpoints with curl once pipeline modules exist
8. Generate `workflows/po_pipeline.json` as a valid n8n v1.x importable workflow
9. Write `README.md` covering all sections listed in the README Requirements above

**Critical notes:**
- The POST /upload-po endpoint must detect file type by extension (.csv vs .pdf)
  and route to the correct ingest function
- Include a background task that logs every processed PO to a local `logs/` directory
- The n8n workflow JSON must use real n8n node types: `n8n-nodes-base.localFileTrigger`,
  `n8n-nodes-base.httpRequest`, `n8n-nodes-base.if`, `n8n-nodes-base.gmail`,
  `n8n-nodes-base.slack`
- README must include a real ASCII architecture diagram, not a placeholder
- Add a `/docs` note in README pointing to FastAPI's auto-generated Swagger UI

**Your final check:**
- [ ] `uvicorn api.main:app --reload --port 8000` starts without errors
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `curl -X POST http://localhost:8000/upload-po -F "file=@data/sample_po.csv"` returns full JSON response
- [ ] `workflows/po_pipeline.json` is valid JSON and contains all 6 nodes
- [ ] README.md is complete with no placeholder sections

---

## Overnight Run Commands

Open 3 separate terminals. Run these commands in order.

### Terminal 1 (Instance 1, run first):
```bash
cd po-pipeline
claude --dangerously-skip-permissions > logs/instance1.log 2>&1
```
First message to paste:
```
You are Instance 1. Read CLAUDE.md fully, find the INSTANCE 1 section, and follow
it exactly. Do not touch any files outside your assigned scope. Begin immediately
with creating the project structure and requirements.txt, then pipeline/models.py.
Do not stop until all your final checks pass.
```

### Terminal 2 (Instance 2, run 15 minutes after Terminal 1):
```bash
cd po-pipeline
claude --dangerously-skip-permissions > logs/instance2.log 2>&1
```
First message to paste:
```
You are Instance 2. Read CLAUDE.md fully, find the INSTANCE 2 section, and follow
it exactly. First check that pipeline/models.py and db/database.py exist. If they
do not exist yet, wait 5 minutes and check again before starting. Do not touch any
files outside your assigned scope. Do not stop until all your final checks pass.
```

### Terminal 3 (Instance 3, run 15 minutes after Terminal 1):
```bash
cd po-pipeline
claude --dangerously-skip-permissions > logs/instance3.log 2>&1
```
First message to paste:
```
You are Instance 3. Read CLAUDE.md fully, find the INSTANCE 3 section, and follow
it exactly. First check that pipeline/models.py exists. If it does not exist yet,
wait 5 minutes and check again before starting. Do not touch any files outside your
assigned scope. Do not stop until all your final checks pass.
```

### Keep your machine awake (run before starting instances):
```bash
# macOS
caffeinate -i &

# Windows (run in PowerShell as admin)
powercfg /change standby-timeout-ac 0
```

### Monitor logs in a 4th terminal:
```bash
tail -f logs/instance1.log logs/instance2.log logs/instance3.log
```

---

## Morning Checklist (Run After Waking Up)

```bash
# 1. Seed the database if not already done
python -c "from db.database import init_db; init_db()"

# 2. Run all tests
pytest tests/ -v

# 3. Start the API
uvicorn api.main:app --reload --port 8000

# 4. Full end-to-end test
curl -X POST http://localhost:8000/upload-po \
  -F "file=@data/sample_po.csv"

# 5. Check stored report (replace PO_NUMBER with value from step 4)
curl http://localhost:8000/report/PO_NUMBER
curl http://localhost:8000/exceptions/PO_NUMBER
```

Final checks:
- [ ] `pytest tests/ -v` all pass
- [ ] API starts without errors
- [ ] CSV upload returns full JSON with validation + exception summary
- [ ] PDF upload also works
- [ ] README.md is complete and accurate
- [ ] `workflows/po_pipeline.json` is valid and importable into n8n

If anything is broken, paste the error from the relevant log file into a fresh
Claude Code session and ask it to fix it.

---

## Final Check Before Stopping

Before you finish, run the following and confirm each passes:

- [ ] `pytest tests/ -v` — all tests pass
- [ ] `uvicorn api.main:app` starts without errors
- [ ] `curl -X POST http://localhost:8000/upload-po -F "file=@data/sample_po.csv"` returns valid JSON
- [ ] `curl http://localhost:8000/report/{po_number}` returns the validation report
- [ ] `curl http://localhost:8000/exceptions/{po_number}` returns the Claude-generated summary
- [ ] README.md is complete and accurate

If any check fails, fix it before stopping. Do not leave broken state.
