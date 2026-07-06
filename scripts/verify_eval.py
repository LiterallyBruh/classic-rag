"""Верификация eval-вопросов против корпуса.

Каждый вопрос обязан иметь gold_match — подстроку, дословно присутствующую
в записях золотой локации (часть+глава / часть+сцена). Скрипт печатает
несовпадения и, если подстрока нашлась в другом месте, подсказывает его.

Запуск: python scripts/verify_eval.py [eval/questions.jsonl]
Выход 0 — все вопросы валидны.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

PROCESSED = Path("data/processed")


def norm(s: str) -> str:
    return s.casefold().replace("ё", "е")


def load_corpus() -> dict[tuple, list[str]]:
    by_loc: dict[tuple, list[str]] = defaultdict(list)
    for path in PROCESSED.glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                key = (r["book"], r["part"], r["chapter"], r.get("scene"))
                text = r["text"]
                if r.get("speaker"):
                    text = f"{r['speaker']}: {text}"
                by_loc[key].append(text)
    return by_loc


def main() -> None:
    q_path = Path(sys.argv[1] if len(sys.argv) > 1 else "eval/questions.jsonl")
    corpus = load_corpus()
    questions = [json.loads(line) for line in q_path.read_text(encoding="utf-8").splitlines()]

    failures = 0
    for i, q in enumerate(questions, 1):
        gold = (q["book"], q.get("part"), q.get("chapter"), q.get("scene"))
        match = norm(q["gold_match"])
        texts = corpus.get(gold)
        if texts is None:
            print(f"[{i}] НЕТ ЛОКАЦИИ {gold}: {q['question'][:60]}")
            failures += 1
            continue
        if any(match in norm(t) for t in texts):
            continue
        failures += 1
        found_at = [loc for loc, ts in corpus.items() if any(match in norm(t) for t in ts)]
        hint = f"; найдено в {found_at[:3]}" if found_at else "; НЕ НАЙДЕНО НИГДЕ"
        print(f"[{i}] МИМО {gold}: «{q['gold_match'][:50]}»{hint}")

    total = len(questions)
    print(f"\n{total - failures}/{total} вопросов валидны")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
