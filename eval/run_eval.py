"""Оценка retrieval: recall@k и MRR по eval/questions.jsonl.

Два критерия попадания:
- span   — текст чанка содержит gold_match (строгий, основной);
- loc    — чанк из золотой локации (часть+глава / часть+сцена).

Запуск:
    python eval/run_eval.py --strategies window paragraph chapter --rerank
Пишет таблицы в stdout; финальные результаты вручную переносятся
в eval/report.md с выводами.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from classic_rag.normalize import CharacterNormalizer
from classic_rag.rerank import Reranker
from classic_rag.retrieval import HybridRetriever

INDEX_ROOT = Path("data/index")
QUESTIONS = Path("eval/questions.jsonl")
KS = (1, 5, 10)


def norm(s: str) -> str:
    return s.casefold().replace("ё", "е")


def is_span_hit(chunk, q) -> bool:
    return norm(q["gold_match"]) in norm(chunk.text)


def is_loc_hit(chunk, q) -> bool:
    if chunk.book != q["book"]:
        return False
    if q.get("scene"):
        return chunk.scene == q["scene"] and chunk.part == q.get("part")
    return chunk.part == q.get("part") and chunk.chapter == q.get("chapter")


def evaluate(questions: list[dict], retriever, normalizer, reranker=None, depth: int = 30):
    span_hits = {k: 0 for k in KS}
    loc_hits = {k: 0 for k in KS}
    mrr_total = 0.0
    t0 = time.time()
    for q in questions:
        expanded = normalizer.expand_query(q["question"], book=q["book"])
        chunks = retriever.search(expanded, k=depth)
        if reranker is not None:
            chunks = reranker.rerank(q["question"], chunks, k=max(KS))
        for k in KS:
            if any(is_span_hit(c, q) for c in chunks[:k]):
                span_hits[k] += 1
            if any(is_loc_hit(c, q) for c in chunks[:k]):
                loc_hits[k] += 1
        for rank, c in enumerate(chunks, 1):
            if is_span_hit(c, q):
                mrr_total += 1.0 / rank
                break
    n = len(questions)
    return {
        "span": {k: span_hits[k] / n for k in KS},
        "loc": {k: loc_hits[k] / n for k in KS},
        "mrr": mrr_total / n,
        "sec_per_q": (time.time() - t0) / n,
    }


def fmt_row(name: str, m: dict) -> str:
    span = " / ".join(f"{m['span'][k]:.2f}" for k in KS)
    loc = " / ".join(f"{m['loc'][k]:.2f}" for k in KS)
    return (
        f"| {name} | {span} | {loc} | {m['mrr']:.2f} | {m['sec_per_q']:.2f} |"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategies", nargs="+", default=["paragraph", "window", "chapter"])
    ap.add_argument("--rerank", action="store_true", help="добавить прогон с реранкером")
    args = ap.parse_args()

    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines()]
    normalizer = CharacterNormalizer()
    reranker = Reranker() if args.rerank else None

    header = (
        f"| конфигурация | span recall@{'/'.join(map(str, KS))} "
        f"| loc recall@{'/'.join(map(str, KS))} | MRR | сек/вопрос |"
    )
    print(f"Вопросов: {len(questions)}\n")
    print(header)
    print("|" + "---|" * 5)
    for strategy in args.strategies:
        retriever = HybridRetriever.load(INDEX_ROOT / strategy)
        m = evaluate(questions, retriever, normalizer)
        print(fmt_row(f"{strategy}, гибрид", m), flush=True)
        if reranker is not None:
            m = evaluate(questions, retriever, normalizer, reranker=reranker)
            print(fmt_row(f"{strategy}, гибрид+rerank", m), flush=True)


if __name__ == "__main__":
    main()
