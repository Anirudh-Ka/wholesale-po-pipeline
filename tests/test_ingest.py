"""Tests for pipeline/ingest.py."""

from __future__ import annotations

import csv
import tempfile
from datetime import date
from pathlib import Path

import pytest

from pipeline.ingest import parse_csv, parse_pdf
from pipeline.models import PODocument


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """Create a minimal valid PO CSV for testing."""
    p = tmp_path / "test_po.csv"
    rows = [
        {
            "po_number": "PO-TEST-001",
            "retailer": "TestRetailer",
            "submitted_date": "2026-05-01",
            "sku": "EDL-W-PUMP-BLK-7",
            "description": "Women's Pump Black Size 7",
            "quantity": "10",
            "unit_price": "28.50",
            "requested_delivery": "2026-06-15",
        },
        {
            "po_number": "PO-TEST-001",
            "retailer": "TestRetailer",
            "submitted_date": "2026-05-01",
            "sku": "EDL-W-SANDAL-TAN-8",
            "description": "Women's Sandal Tan Size 8",
            "quantity": "5",
            "unit_price": "22.00",
            "requested_delivery": "2026-06-15",
        },
    ]
    with p.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return p


@pytest.fixture()
def malformed_csv(tmp_path: Path) -> Path:
    """CSV with one bad row (non-numeric quantity) and one good row."""
    p = tmp_path / "malformed.csv"
    lines = [
        "po_number,retailer,submitted_date,sku,description,quantity,unit_price,requested_delivery\n",
        "PO-TEST-001,TestRetailer,2026-05-01,EDL-W-PUMP-BLK-7,Pump,abc,28.50,2026-06-15\n",
        "PO-TEST-001,TestRetailer,2026-05-01,EDL-W-SANDAL-TAN-8,Sandal,5,22.00,2026-06-15\n",
    ]
    p.write_text("".join(lines), encoding="utf-8")
    return p


def test_parse_csv_returns_po_document(sample_csv: Path) -> None:
    """parse_csv should return a valid PODocument."""
    result = parse_csv(sample_csv)
    assert isinstance(result, PODocument)
    assert result.po_number == "PO-TEST-001"
    assert result.retailer == "TestRetailer"
    assert len(result.line_items) == 2


def test_parse_csv_line_item_fields(sample_csv: Path) -> None:
    """Line items should have correct sku, quantity, and price."""
    result = parse_csv(sample_csv)
    first = result.line_items[0]
    assert first.sku == "EDL-W-PUMP-BLK-7"
    assert first.quantity == 10
    assert first.unit_price == pytest.approx(28.50)
    assert first.requested_delivery == date(2026, 6, 15)


def test_parse_csv_skips_malformed_rows(malformed_csv: Path) -> None:
    """Malformed rows should be skipped; valid rows still parsed."""
    result = parse_csv(malformed_csv)
    assert len(result.line_items) == 1
    assert result.line_items[0].sku == "EDL-W-SANDAL-TAN-8"


def test_parse_csv_missing_file_raises() -> None:
    """parse_csv should raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        parse_csv("/nonexistent/path/po.csv")


def test_parse_csv_real_sample() -> None:
    """parse_csv should successfully parse the real sample_po.csv."""
    sample = Path(__file__).parent.parent / "data" / "sample_po.csv"
    if not sample.exists():
        pytest.skip("data/sample_po.csv not found")
    result = parse_csv(sample)
    assert result.po_number == "PO-JCP-2026-0412"
    assert len(result.line_items) == 12


def test_parse_pdf_real_sample() -> None:
    """parse_pdf should return a PODocument from the real sample_po.pdf."""
    sample = Path(__file__).parent.parent / "data" / "sample_po.pdf"
    if not sample.exists():
        pytest.skip("data/sample_po.pdf not found")
    result = parse_pdf(sample)
    assert isinstance(result, PODocument)
    assert len(result.line_items) > 0
