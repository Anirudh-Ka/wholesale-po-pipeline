"""Validate a PODocument against the inventory database."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from db.database import DEFAULT_DB_PATH, get_inventory_item
from pipeline.models import (
    LineItem,
    LineValidation,
    PODocument,
    ValidationReport,
    ValidationStatus,
)

# Acceptable price tolerance (5 %)
_PRICE_TOLERANCE = 0.05


def validate_po(po: PODocument, db_path: str | Path | None = None) -> ValidationReport:
    """Validate each line item in *po* against inventory and return a report."""
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not resolved_db.exists():
        raise FileNotFoundError(
            f"Inventory database not found at {resolved_db}. "
            "Run: python -c \"from db.database import init_db; init_db()\""
        )

    results: list[LineValidation] = []
    for item in po.line_items:
        results.append(_validate_line(item, resolved_db))

    passed = sum(1 for r in results if r.status == ValidationStatus.OK)
    return ValidationReport(
        po_number=po.po_number,
        validated_at=datetime.utcnow(),
        total_lines=len(results),
        passed=passed,
        flagged=len(results) - passed,
        line_results=results,
    )


def _validate_line(item: LineItem, db_path: Path) -> LineValidation:
    """Return a LineValidation for a single line item."""
    row = get_inventory_item(item.sku, db_path)

    if row is None:
        return LineValidation(
            line_item=item,
            status=ValidationStatus.INVALID_SKU,
            available_stock=None,
            expected_price=None,
            notes=f"SKU '{item.sku}' not found in inventory.",
        )

    stock: int = int(row["stock_count"])
    wholesale: float = float(row["wholesale_price"])
    max_order_qty: int = int(row["max_order_qty"])

    if item.quantity > max_order_qty:
        return LineValidation(
            line_item=item,
            status=ValidationStatus.QUANTITY_EXCEEDED,
            available_stock=stock,
            expected_price=wholesale,
            notes=(
                f"Requested quantity {item.quantity} exceeds maximum order limit "
                f"of {max_order_qty} units per SKU."
            ),
        )

    if stock < item.quantity:
        return LineValidation(
            line_item=item,
            status=ValidationStatus.STOCKOUT,
            available_stock=stock,
            expected_price=wholesale,
            notes=(
                f"Insufficient stock: {stock} units available, "
                f"{item.quantity} requested."
            ),
        )

    price_diff = abs(item.unit_price - wholesale) / wholesale
    if price_diff > _PRICE_TOLERANCE:
        direction = "below" if item.unit_price < wholesale else "above"
        return LineValidation(
            line_item=item,
            status=ValidationStatus.PRICE_MISMATCH,
            available_stock=stock,
            expected_price=wholesale,
            notes=(
                f"PO price ${item.unit_price:.2f} is {price_diff:.1%} {direction} "
                f"wholesale price ${wholesale:.2f}."
            ),
        )

    return LineValidation(
        line_item=item,
        status=ValidationStatus.OK,
        available_stock=stock,
        expected_price=wholesale,
        notes="All checks passed.",
    )
