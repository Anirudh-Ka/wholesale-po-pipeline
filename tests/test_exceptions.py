"""Tests for pipeline/exceptions.py (Claude API mocked)."""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from pipeline.exceptions import generate_exception_summary
from pipeline.models import (
    ExceptionSummary,
    LineItem,
    LineValidation,
    ValidationReport,
    ValidationStatus,
)


def _make_report(flagged_count: int = 3) -> ValidationReport:
    """Build a ValidationReport with a mix of passed and flagged lines."""
    base_item = LineItem(
        sku="EDL-W-PUMP-BLK-7",
        description="Pump Black 7",
        retailer="JCPenney",
        quantity=10,
        unit_price=28.50,
        requested_delivery=date(2026, 6, 15),
    )
    results = [
        LineValidation(
            line_item=base_item,
            status=ValidationStatus.OK,
            available_stock=100,
            expected_price=28.50,
            notes="All checks passed.",
        )
    ]
    statuses = [
        (ValidationStatus.STOCKOUT,    "Insufficient stock."),
        (ValidationStatus.PRICE_MISMATCH, "Price differs by 15%."),
        (ValidationStatus.INVALID_SKU, "SKU not found."),
    ]
    for i in range(min(flagged_count, len(statuses))):
        status, note = statuses[i]
        results.append(
            LineValidation(
                line_item=LineItem(
                    sku=f"EDL-FAKE-{i:03d}",
                    description=f"Fake Item {i}",
                    retailer="JCPenney",
                    quantity=50,
                    unit_price=19.99,
                    requested_delivery=date(2026, 6, 30),
                ),
                status=status,
                available_stock=0,
                expected_price=22.00,
                notes=note,
            )
        )
    return ValidationReport(
        po_number="PO-TEST-001",
        validated_at=datetime(2026, 5, 1, 12, 0, 0),
        total_lines=len(results),
        passed=1,
        flagged=flagged_count,
        line_results=results,
    )


def _mock_response(narrative: str, actions: list[str], email: str) -> MagicMock:
    """Return a mock Anthropic Message object."""
    response_json = json.dumps(
        {"narrative": narrative, "recommended_actions": actions, "email_draft": email}
    )
    content_block = MagicMock()
    content_block.text = response_json
    message = MagicMock()
    message.content = [content_block]
    return message


@pytest.fixture()
def mock_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch the Anthropic client so no real API calls are made."""
    fake_message = _mock_response(
        narrative="Three line items were flagged for exceptions.",
        actions=["Contact buyer about stockouts.", "Verify SKUs.", "Correct pricing."],
        email="Dear Buyer,\n\nWe identified issues with your order.\n\nBest regards,\nEDL Ops",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake_message

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")
    with patch("pipeline.exceptions.anthropic.Anthropic", return_value=mock_client):
        yield mock_client


def test_no_exceptions_returns_clean_summary() -> None:
    """When flagged == 0, no Claude call is made and narrative says all passed."""
    report = _make_report(flagged_count=0)
    summary = generate_exception_summary(report)
    assert isinstance(summary, ExceptionSummary)
    assert "passed" in summary.narrative.lower()
    assert summary.flagged == 0 if hasattr(summary, "flagged") else True


def test_generate_summary_calls_claude(mock_anthropic: MagicMock) -> None:
    """When lines are flagged, generate_exception_summary should call Claude."""
    report = _make_report(flagged_count=3)
    summary = generate_exception_summary(report)
    mock_anthropic.messages.create.assert_called_once()
    assert isinstance(summary, ExceptionSummary)


def test_summary_has_required_fields(mock_anthropic: MagicMock) -> None:
    """The returned ExceptionSummary should have all required fields populated."""
    report = _make_report(flagged_count=3)
    summary = generate_exception_summary(report)
    assert summary.po_number == "PO-TEST-001"
    assert len(summary.narrative) > 0
    assert len(summary.recommended_actions) > 0
    assert len(summary.email_draft) > 0


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """EnvironmentError should be raised when ANTHROPIC_API_KEY is missing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    report = _make_report(flagged_count=1)
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        generate_exception_summary(report)
