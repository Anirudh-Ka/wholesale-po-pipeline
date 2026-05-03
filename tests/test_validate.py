"""Tests for pipeline/validate.py."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from db.database import init_db
from pipeline.models import LineItem, PODocument, ValidationStatus
from pipeline.validate import validate_po


@pytest.fixture()
def seeded_db(tmp_path: Path) -> Path:
    """Initialise a temporary database and seed it with test inventory."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.executemany(
        "INSERT OR REPLACE INTO inventory (sku, description, color, size, stock_count, wholesale_price, category) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("EDL-W-PUMP-BLK-7",   "Pump Black 7",   "BLK", "7",   100, 28.50, "PUMP"),
            ("EDL-W-SANDAL-TAN-8", "Sandal Tan 8",   "TAN", "8",   50,  22.00, "SANDAL"),
            ("EDL-W-BOOT-BLK-7",   "Boot Black 7",   "BLK", "7",   5,   42.00, "BOOT"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def _make_po(*items: dict) -> PODocument:
    """Build a minimal PODocument from a list of line item dicts."""
    line_items = [
        LineItem(
            sku=it["sku"],
            description=it.get("description", "Test Item"),
            retailer="TestRetailer",
            quantity=it["quantity"],
            unit_price=it["unit_price"],
            requested_delivery=date(2026, 6, 15),
        )
        for it in items
    ]
    return PODocument(
        po_number="PO-TEST-001",
        retailer="TestRetailer",
        submitted_date=date(2026, 5, 1),
        line_items=line_items,
    )


def test_clean_line_passes(seeded_db: Path) -> None:
    """A line with valid SKU, sufficient stock, and correct price should be OK."""
    po = _make_po({"sku": "EDL-W-PUMP-BLK-7", "quantity": 10, "unit_price": 28.50})
    report = validate_po(po, seeded_db)
    assert report.passed == 1
    assert report.flagged == 0
    assert report.line_results[0].status == ValidationStatus.OK


def test_invalid_sku_flagged(seeded_db: Path) -> None:
    """An unknown SKU should produce INVALID_SKU status."""
    po = _make_po({"sku": "EDL-FAKE-SKU-999", "quantity": 5, "unit_price": 20.00})
    report = validate_po(po, seeded_db)
    assert report.line_results[0].status == ValidationStatus.INVALID_SKU


def test_stockout_flagged(seeded_db: Path) -> None:
    """Requesting more than available stock should produce STOCKOUT."""
    po = _make_po({"sku": "EDL-W-BOOT-BLK-7", "quantity": 50, "unit_price": 42.00})
    report = validate_po(po, seeded_db)
    assert report.line_results[0].status == ValidationStatus.STOCKOUT


def test_price_mismatch_flagged(seeded_db: Path) -> None:
    """A price more than 5% below wholesale should produce PRICE_MISMATCH."""
    po = _make_po({"sku": "EDL-W-PUMP-BLK-7", "quantity": 10, "unit_price": 20.00})
    report = validate_po(po, seeded_db)
    assert report.line_results[0].status == ValidationStatus.PRICE_MISMATCH


def test_quantity_exceeded_flagged(seeded_db: Path) -> None:
    """Requesting more than max order qty (200) should produce QUANTITY_EXCEEDED."""
    po = _make_po({"sku": "EDL-W-PUMP-BLK-7", "quantity": 250, "unit_price": 28.50})
    report = validate_po(po, seeded_db)
    assert report.line_results[0].status == ValidationStatus.QUANTITY_EXCEEDED


def test_mixed_po(seeded_db: Path) -> None:
    """Mixed PO should count passed and flagged correctly."""
    po = _make_po(
        {"sku": "EDL-W-PUMP-BLK-7",   "quantity": 10,  "unit_price": 28.50},
        {"sku": "EDL-FAKE-SKU-999",    "quantity": 5,   "unit_price": 20.00},
        {"sku": "EDL-W-SANDAL-TAN-8",  "quantity": 5,   "unit_price": 22.00},
    )
    report = validate_po(po, seeded_db)
    assert report.passed == 2
    assert report.flagged == 1
    assert report.total_lines == 3


def test_missing_db_raises(tmp_path: Path) -> None:
    """validate_po should raise FileNotFoundError when DB is absent."""
    po = _make_po({"sku": "EDL-W-PUMP-BLK-7", "quantity": 1, "unit_price": 28.50})
    with pytest.raises(FileNotFoundError):
        validate_po(po, tmp_path / "nonexistent.db")
