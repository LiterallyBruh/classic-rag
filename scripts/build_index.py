"""Построение поискового индекса из data/processed/*.jsonl.

Пример:
    python scripts/build_index.py --strategy window
    python scripts/build_index.py --strategy paragraph --no-dense  # быстро, только BM25

Выход: data/index/<strategy>/ (chunks.jsonl, embeddings.npy, meta.json).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from classic_rag.chunking import STRATEGIES, chunk_records
from classic_rag.retrieval import HybridRetriever

PROCESSED = Path("data/processed")
INDEX_ROOT = Path("data/index")


def load_records() -> list[dict]:
    records: list[dict] = []
    for path in sorted(PROCESSED.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            records.extend(json.loads(line) for line in f)
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategy", choices=sorted(STRATEGIES), default="window")
    ap.add_argument("--no-dense", action="store_true", help="только BM25, без эмбеддингов")
    args = ap.parse_args()

    records = load_records()
    chunks = chunk_records(records, args.strategy)
    words = [len(c.text.split()) for c in chunks]
    print(
        f"Стратегия {args.strategy}: {len(chunks)} чанков из {len(records)} записей; "
        f"слов/чанк: медиана {sorted(words)[len(words) // 2]}, макс {max(words)}"
    )

    retriever = HybridRetriever(chunks) if args.no_dense else HybridRetriever.build(chunks)

    out = INDEX_ROOT / args.strategy
    retriever.save(out)
    print(f"Индекс сохранён в {out}")


if __name__ == "__main__":
    main()
