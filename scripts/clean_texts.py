"""Очистка HTML и структурная разметка: часть → глава → абзацы.

Выход: data/processed/<book>.jsonl, где каждая строка —
{"book": ..., "part": ..., "chapter": ..., "para_id": ..., "text": ...}

Структурные ссылки (часть/глава) — основа точного цитирования в ответах.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")

# Паттерны заголовков различаются между изданиями — уточняются после
# визуальной проверки сырых файлов (см. notebooks/01_eda.ipynb).
PART_RE = re.compile(r"^\s*(ЧАСТЬ|Часть)\s+([А-ЯЁIVX]+)", re.M)
CHAPTER_RE = re.compile(r"^\s*(ГЛАВА|Глава)?\s*([IVXLC]+)\s*\.?\s*$", re.M)


def html_to_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n")


def split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text)]
    return [p for p in paras if len(p) > 1]


def process_book(path: Path) -> list[dict]:
    """Наивная структурная разметка; для «Фауста» (драма) переопределяется
    в process_faust — там сегментация по сценам и репликам."""
    text = html_to_text(path)
    records: list[dict] = []
    part, chapter = "0", "0"
    for i, para in enumerate(split_paragraphs(text)):
        if m := PART_RE.match(para):
            part, chapter = m.group(2), "0"
            continue
        if m := CHAPTER_RE.match(para):
            chapter = m.group(2)
            continue
        records.append(
            {
                "book": path.stem,
                "part": part,
                "chapter": chapter,
                "para_id": i,
                "text": para,
            }
        )
    return records


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(RAW_DIR.glob("*.html")):
        records = process_book(path)
        out = OUT_DIR / f"{path.stem}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{path.stem}: {len(records)} абзацев -> {out}")


if __name__ == "__main__":
    main()
