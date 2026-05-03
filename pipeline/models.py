"""Pydantic models shared across the entire po-pipeline."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item from a purchase order."""

    sku: str
    description: str
    retailer: str
    quantity: int
    unit_price: float
    requested_delivery: date


class PODocument(BaseModel):
    """A parsed purchase order document."""

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
    """Validation result for a single line item."""

    line_item: LineItem
    status: ValidationStatus
    available_stock: int | None = None
    expected_price: float | None = None
    notes: str


class ValidationReport(BaseModel):
    """Full validation report for a purchase order."""

    po_number: str
    validated_at: datetime
    total_lines: int
    passed: int
    flagged: int
    line_results: list[LineValidation]


class ExceptionSummary(BaseModel):
    """Claude-generated exception summary for a purchase order."""

    po_number: str
    generated_at: datetime
    narrative: str
    recommended_actions: list[str]
    email_draft: str
