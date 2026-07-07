"""Сборка конкурсного описания: docs/description.md -> docs/description.pdf.

Конкурс требует PDF до 3 страниц («задача, данные, методы, результаты»).
Markdown остаётся источником правды и версионируется; PDF — генерируемый
артефакт. Шрифт — DejaVu (кириллица), берётся из пакета matplotlib.

Запуск: python scripts/build_description_pdf.py
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "description.md"
OUT = ROOT / "docs" / "description.pdf"

FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", FONTS / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONTS / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Italic", FONTS / "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFontFamily(
    "DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Italic"
)

BODY = ParagraphStyle(
    "body", fontName="DejaVu", fontSize=9.5, leading=13, spaceAfter=5, alignment=4
)
H1 = ParagraphStyle(
    "h1", parent=BODY, fontName="DejaVu-Bold", fontSize=14, leading=17,
    spaceAfter=8, alignment=0,
)
H2 = ParagraphStyle(
    "h2", parent=BODY, fontName="DejaVu-Bold", fontSize=11.5, leading=14,
    spaceBefore=9, spaceAfter=5, alignment=0,
)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=14, bulletIndent=4)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=11, spaceAfter=0)


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return re.sub(r"`([^`]+)`", r"<font face='DejaVu'>\1</font>", text)


def flush_table(rows: list[list[str]], story: list) -> None:
    data = [[Paragraph(inline(c), CELL) for c in row] for row in rows]
    t = Table(data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.93, 0.93)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [Spacer(1, 3), t, Spacer(1, 6)]


def build() -> None:
    story: list = []
    table_rows: list[list[str]] = []
    para: list[str] = []  # markdown переносит абзац по строкам — склеиваем

    def flush_para() -> None:
        if para:
            story.append(Paragraph(inline(" ".join(para)), BODY))
            para.clear()

    for raw in SRC.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            flush_para()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                table_rows.append(cells)
            continue
        if table_rows:
            flush_table(table_rows, story)
            table_rows = []
        if not line:
            flush_para()
        elif line.startswith("## "):
            flush_para()
            story.append(Paragraph(inline(line[3:]), H2))
        elif line.startswith("# "):
            flush_para()
            story.append(Paragraph(inline(line[2:]), H1))
        elif line.startswith("- "):
            flush_para()
            story.append(Paragraph(inline(line[2:]), BULLET, bulletText="•"))
        elif line.startswith("  ") and story and not para:
            # продолжение элемента списка (отступ)
            prev = story.pop()
            story.append(Paragraph(prev.text + " " + inline(line.strip()), BULLET,
                                   bulletText="•"))
        else:
            para.append(line.strip())
    flush_para()
    if table_rows:
        flush_table(table_rows, story)

    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title="ClassicRAG — описание проекта", author="Junior ML Contest",
    )
    doc.build(story)
    print(f"OK: {OUT}")


if __name__ == "__main__":
    build()
