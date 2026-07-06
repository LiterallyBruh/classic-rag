"""Бутстрап окружения демо: корпус -> очистка -> индекс, если их ещё нет.

Идемпотентен: готовые артефакты не пересоздаются. Используется при старте
Docker-контейнера и HF Space (data/ не хранится в git — см. D-001).

Запуск: python scripts/bootstrap.py [--strategy window]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
INDEX = Path("data/index")
N_BOOKS = 4


def run(script: str, *args: str) -> None:
    print(f"[bootstrap] {script} {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, script, *args], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategy", default="window")
    args = ap.parse_args()

    index_dir = INDEX / args.strategy
    # retrieval'у нужен только индекс (chunks.jsonl + embeddings.npy) —
    # если он уже есть (напр., доставлен в репозитории HF Space),
    # корпус не скачиваем вовсе
    if (index_dir / "embeddings.npy").exists() and (index_dir / "chunks.jsonl").exists():
        print("[bootstrap] индекс уже есть, пропускаю", flush=True)
        return
    if len(list(RAW.glob("*.html"))) < N_BOOKS:
        run("scripts/download_texts.py")
    if len(list(PROCESSED.glob("*.jsonl"))) < N_BOOKS:
        run("scripts/clean_texts.py")
    run("scripts/build_index.py", "--strategy", args.strategy)
    print("[bootstrap] готово", flush=True)


if __name__ == "__main__":
    main()
