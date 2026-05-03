"""Generate Claude-powered exception summaries for flagged purchase orders."""

from __future__ import annotations

import json
import os
from datetime import datetime

import anthropic
from dotenv import load_dotenv

from pipeline.models import ExceptionSummary, LineValidation, ValidationReport, ValidationStatus

load_dotenv()

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048

_SYSTEM_PROMPT = (
    "You are an operations assistant for Evolution Design Lab, a wholesale footwear company "
    "that supplies retailers such as JCPenney, Famous Footwear, and DSW. "
    "You review purchase order validation reports and help the operations team communicate "
    "issues clearly and professionally."
)


def generate_exception_summary(report: ValidationReport) -> ExceptionSummary:
    """Call Claude to summarise flagged line items and draft a buyer email.

    Returns an ExceptionSummary with narrative, recommended actions, and email draft.
    If no lines are flagged, returns a summary indicating all lines passed.
    """
    if report.flagged == 0:
        return ExceptionSummary(
            po_number=report.po_number,
            generated_at=datetime.utcnow(),
            narrative="All line items passed validation. No exceptions to report.",
            recommended_actions=["Proceed with order fulfillment."],
            email_draft=(
                f"Dear Buyer,\n\nWe are pleased to confirm that purchase order "
                f"{report.po_number} has passed all validation checks. "
                f"We will proceed with fulfillment as requested.\n\nBest regards,\n"
                f"Evolution Design Lab Operations Team"
            ),
        )

    flagged_lines = [r for r in report.line_results if r.status != ValidationStatus.OK]
    context = _build_context(report, flagged_lines)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Add it to .env or set it as an environment variable."
        )

    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"Here is the validation report for purchase order {report.po_number}:\n\n"
        f"{context}\n\n"
        "Please respond with a JSON object containing exactly these three keys:\n"
        "1. \"narrative\": A plain-English paragraph (3-5 sentences) summarising the "
        "exceptions for an operations manager.\n"
        "2. \"recommended_actions\": A JSON array of 3-5 concise action items (strings) "
        "for the operations team.\n"
        "3. \"email_draft\": A professional email draft addressed to the buyer explaining "
        "the issues and proposed resolutions.\n\n"
        "Return only valid JSON, no markdown fences."
    )

    message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON response: {exc}\n\nRaw: {raw}") from exc

    return ExceptionSummary(
        po_number=report.po_number,
        generated_at=datetime.utcnow(),
        narrative=parsed.get("narrative", ""),
        recommended_actions=parsed.get("recommended_actions", []),
        email_draft=parsed.get("email_draft", ""),
    )


def _build_context(report: ValidationReport, flagged: list[LineValidation]) -> str:
    """Format flagged line items as readable text for the Claude prompt."""
    lines = [
        f"PO Number: {report.po_number}",
        f"Total lines: {report.total_lines}",
        f"Passed: {report.passed}",
        f"Flagged: {report.flagged}",
        "",
        "Flagged line items:",
    ]
    for i, result in enumerate(flagged, start=1):
        item = result.line_item
        lines.append(
            f"{i}. SKU={item.sku} | Qty={item.quantity} | "
            f"Price=${item.unit_price:.2f} | Status={result.status.value} | "
            f"Notes={result.notes}"
        )
    return "\n".join(lines)
