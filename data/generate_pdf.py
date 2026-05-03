"""Generate data/sample_po.pdf from sample_po.csv using reportlab."""

from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_DATA_DIR = Path(__file__).parent
_CSV = _DATA_DIR / "sample_po.csv"
_PDF = _DATA_DIR / "sample_po.pdf"


def generate() -> None:
    """Read sample_po.csv and write a formatted sample_po.pdf."""
    doc = SimpleDocTemplate(
        str(_PDF),
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("EVOLUTION DESIGN LAW WHOLESALE", styles["Title"]))
    story.append(Paragraph("Purchase Order", styles["h2"]))
    story.append(Spacer(1, 0.1 * inch))

    rows = list(csv.DictReader(_CSV.open(encoding="utf-8")))
    if not rows:
        raise ValueError("sample_po.csv is empty")

    first = rows[0]
    story.append(Paragraph(f"PO Number: {first['po_number']}", styles["Normal"]))
    story.append(Paragraph(f"Retailer: {first['retailer']}", styles["Normal"]))
    story.append(Paragraph(f"Date: {first['submitted_date']}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    headers = ["SKU", "Description", "Qty", "Unit Price", "Delivery"]
    table_data = [headers]
    for row in rows:
        table_data.append([
            row["sku"],
            row["description"],
            row["quantity"],
            f"${float(row['unit_price']):.2f}",
            row["requested_delivery"],
        ])

    col_widths = [1.6 * inch, 2.4 * inch, 0.5 * inch, 0.9 * inch, 1.1 * inch]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",   (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("ALIGN",      (2, 0), (3, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(tbl)
    doc.build(story)
    print(f"PDF written to {_PDF}")


if __name__ == "__main__":
    generate()
