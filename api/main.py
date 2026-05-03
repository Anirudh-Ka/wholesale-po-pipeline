"""FastAPI application for the wholesale PO processing pipeline."""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from db.database import DEFAULT_DB_PATH, get_processed_po, init_db, save_processed_po
from pipeline.exceptions import generate_exception_summary
from pipeline.ingest import parse_csv, parse_pdf
from pipeline.models import ExceptionSummary, ValidationReport
from pipeline.validate import validate_po

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_LOGS_DIR      = Path(__file__).parent.parent / "logs"
_DASHBOARD_PATH = Path(__file__).parent.parent / "dashboard.html"
_LOGS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Wholesale PO Processing Pipeline",
    description="AI-powered purchase order validation and exception summarisation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise the database on startup."""
    init_db()


@app.get("/")
async def dashboard() -> FileResponse:
    """Serve the PO Pipeline dashboard HTML."""
    return FileResponse(str(_DASHBOARD_PATH), media_type="text/html")


@app.get("/health")
async def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}


@app.post("/upload-po")
async def upload_po(file: UploadFile = File(...)) -> JSONResponse:
    """Accept a CSV or PDF purchase order, run the full pipeline, and return results.

    Stores results in the processed_pos table and logs to the logs/ directory.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".csv", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only .csv and .pdf files are supported.")

    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(content)

    try:
        if suffix == ".csv":
            po = parse_csv(tmp_path)
        else:
            po = parse_pdf(tmp_path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    try:
        report = validate_po(po, DEFAULT_DB_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    exception_summary: ExceptionSummary | None = None
    try:
        exception_summary = generate_exception_summary(report)
    except EnvironmentError as exc:
        # Missing API key is a configuration error; only fatal when there are flagged lines
        # that actually need a Claude-generated summary.
        if report.flagged > 0:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        logger.warning("No API key — skipping summary for clean order: %s", exc)
    except Exception as exc:
        logger.error("Exception generation failed: %s", exc, exc_info=True)
        if report.flagged > 0:
            raise HTTPException(
                status_code=500,
                detail=f"Exception summary generation failed: {exc}",
            ) from exc

    status = "flagged" if report.flagged > 0 else "clean"
    validation_json = report.model_dump_json()
    exception_json = exception_summary.model_dump_json() if exception_summary else None

    save_processed_po(
        po_number=po.po_number,
        retailer=po.retailer,
        submitted_date=po.submitted_date.isoformat(),
        processed_at=datetime.utcnow().isoformat(),
        status=status,
        validation_json=validation_json,
        exception_json=exception_json,
    )

    _log_result(po.po_number, status, report, exception_summary)

    return JSONResponse(
        content={
            "po_number": po.po_number,
            "status": status,
            "validation_report": json.loads(validation_json),
            "exception_summary": json.loads(exception_json) if exception_json else None,
        }
    )


@app.get("/report/{po_number}")
async def get_report(po_number: str) -> JSONResponse:
    """Return the stored ValidationReport for a given PO number."""
    row = get_processed_po(po_number)
    if row is None:
        raise HTTPException(status_code=404, detail=f"PO '{po_number}' not found.")
    if not row["validation_json"]:
        raise HTTPException(status_code=404, detail=f"No validation report for PO '{po_number}'.")
    return JSONResponse(content=json.loads(row["validation_json"]))


@app.get("/exceptions/{po_number}")
async def get_exceptions(po_number: str) -> JSONResponse:
    """Return the stored ExceptionSummary for a given PO number."""
    row = get_processed_po(po_number)
    if row is None:
        raise HTTPException(status_code=404, detail=f"PO '{po_number}' not found.")
    if not row["exception_json"]:
        if row["status"] == "flagged":
            raise HTTPException(
                status_code=404,
                detail=(
                    "Exception summary was not generated for this PO. "
                    "Re-upload with ANTHROPIC_API_KEY set in .env."
                ),
            )
        return JSONResponse(content={"message": "no exceptions"})
    return JSONResponse(content=json.loads(row["exception_json"]))


def _log_result(
    po_number: str,
    status: str,
    report: ValidationReport,
    summary: ExceptionSummary | None,
) -> None:
    """Write a JSON log entry for the processed PO to logs/."""
    log_file = _LOGS_DIR / f"{po_number}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    entry = {
        "po_number": po_number,
        "status": status,
        "processed_at": datetime.utcnow().isoformat(),
        "flagged": report.flagged,
        "passed": report.passed,
        "has_exception_summary": summary is not None,
    }
    try:
        log_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write log file: %s", exc)
