"""Ingest purchase orders from CSV or PDF into PODocument models."""

from __future__ import annotations

import csv
import logging
import re
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from pipeline.models import LineItem, PODocument

logger = logging.getLogger(__name__)


def parse_csv(file_path: str | Path) -> PODocument:
    """Parse a CSV purchase order file and return a PODocument.

    Expected columns: po_number, retailer, submitted_date, sku, description,
    quantity, unit_price, requested_delivery.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    line_items: list[LineItem] = []
    po_number = ""
    retailer = ""
    submitted_date: date | None = None

    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row_num, row in enumerate(reader, start=2):
                try:
                    po_number = row["po_number"].strip()
                    retailer = row["retailer"].strip()
                    submitted_date = date.fromisoformat(row["submitted_date"].strip())
                    item = LineItem(
                        sku=row["sku"].strip(),
                        description=row["description"].strip(),
                        retailer=row["retailer"].strip(),
                        quantity=int(float(row["quantity"].strip())),
                        unit_price=float(row["unit_price"].strip()),
                        requested_delivery=date.fromisoformat(row["requested_delivery"].strip()),
                    )
                    line_items.append(item)
                except (KeyError, ValueError) as exc:
                    logger.warning("Skipping malformed row %d: %s", row_num, exc)
    except OSError as exc:
        raise OSError(f"Cannot read CSV file {path}: {exc}") from exc

    if not line_items:
        raise ValueError(f"No valid line items found in {path}")

    return PODocument(
        po_number=po_number,
        retailer=retailer,
        submitted_date=submitted_date or date.today(),
        line_items=line_items,
    )


def parse_pdf(file_path: str | Path) -> PODocument:
    """Parse a PDF purchase order file and return a PODocument.

    Extracts text with pypdf, then parses structured fields with regex.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError(f"Cannot read PDF {path}: {exc}") from exc

    po_number = _extract_field(text, r"PO Number[:\s]+([A-Z0-9\-]+)")
    retailer = _extract_field(text, r"Retailer[:\s]+([^\n]+)")
    submitted_str = _extract_field(text, r"Date[:\s]+(\d{4}-\d{2}-\d{2})")
    submitted_date = date.fromisoformat(submitted_str) if submitted_str else date.today()

    line_items = _parse_pdf_line_items(text, retailer or "Unknown")

    if not line_items:
        raise ValueError(f"No valid line items found in PDF {path}")

    return PODocument(
        po_number=po_number or "UNKNOWN",
        retailer=retailer or "Unknown",
        submitted_date=submitted_date,
        line_items=line_items,
    )


def _extract_field(text: str, pattern: str) -> str:
    """Extract a single field from PDF text using a regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_pdf_line_items(text: str, retailer: str) -> list[LineItem]:
    """Extract line items from the tabular section of PDF text."""
    items: list[LineItem] = []
    # Pattern: SKU | description | qty | price | delivery_date
    pattern = re.compile(
        r"(EDL-[A-Z0-9.\-]+)\s+"
        r"(.+?)\s+"
        r"(\d+)\s+"
        r"\$?([\d.]+)\s+"
        r"(\d{4}-\d{2}-\d{2})"
    )
    for match in pattern.finditer(text):
        try:
            items.append(
                LineItem(
                    sku=match.group(1).strip(),
                    description=match.group(2).strip(),
                    retailer=retailer,
                    quantity=int(match.group(3)),
                    unit_price=float(match.group(4)),
                    requested_delivery=date.fromisoformat(match.group(5)),
                )
            )
        except ValueError as exc:
            logger.warning("Skipping malformed PDF line item: %s", exc)
    return items
