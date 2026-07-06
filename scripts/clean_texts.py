"""Очистка HTML и структурная разметка: часть → глава → абзацы.

Выход: data/processed/<book>.jsonl, одна строка — один абзац (для романов)
или одна реплика (для «Фауста») с полным структурным адресом.
Логика парсинга — в src/classic_rag/cleaning.py (покрыта тестами).
"""

from __future__ import annotations

import json
from pathlib import Path

from classic_rag.cleaning import parse_faust, parse_novel

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(RAW_DIR.glob("*.html")):
        raw = path.read_text(encoding="utf-8")
        parser = parse_faust if path.stem.startswith("faust") else parse_novel
        records = parser(raw, path.stem)
        out = OUT_DIR / f"{path.stem}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{path.stem}: {len(records)} записей -> {out}")


if __name__ == "__main__":
    main()
