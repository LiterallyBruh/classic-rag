"""Гибридный retrieval: BM25 + dense-эмбеддинги, слияние через RRF.

Дизайн-решения (аргументация для защиты, подробнее в docs/decisions.md):
- BM25 ловит точные редкие термины (имена, топонимы), dense — перефразировки
  и интерпретационные вопросы; по литературным текстам ни один из них
  не доминирует, поэтому гибрид (см. eval/report.md, таблица сравнения).
- RRF (reciprocal rank fusion) выбран вместо взвешенной суммы score'ов,
  потому что не требует калибровки шкал между BM25 и косинусной близостью.
- Индекс хранится файлами (chunks.jsonl + embeddings.npy): корпус ~10^4
  чанков, полный перебор косинусов на numpy — миллисекунды; векторная БД
  здесь была бы лишней инфраструктурой (D-007).
- Энкодер загружается лениво: BM25-поиск и тесты не требуют скачивания
  модели.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from razdel import tokenize

from .chunking import Chunk

DENSE_MODEL = "intfloat/multilingual-e5-base"

# Callable[(тексты, is_query), матрица нормированных эмбеддингов]
Encoder = Callable[[list[str], bool], np.ndarray]


def bm25_tokens(text: str) -> list[str]:
    """razdel вместо split: отделяет пунктуацию («Раскольников,» -> «раскольников»)."""
    return [t.text.lower() for t in tokenize(text)]


def _default_encoder() -> Encoder:
    from sentence_transformers import SentenceTransformer  # тяжёлый импорт — лениво

    model = SentenceTransformer(DENSE_MODEL)

    def encode(texts: list[str], is_query: bool) -> np.ndarray:
        prefix = "query: " if is_query else "passage: "  # префиксы обязательны для e5
        return model.encode(
            [prefix + t for t in texts],
            normalize_embeddings=True,
            show_progress_bar=not is_query,
        )

    return encode


class HybridRetriever:
    def __init__(
        self,
        chunks: list[Chunk],
        embeddings: np.ndarray | None = None,
        encoder: Encoder | None = None,
    ) -> None:
        self.chunks = chunks
        self._bm25 = BM25Okapi([bm25_tokens(c.text) for c in chunks])
        self._embeddings = embeddings
        self._encoder = encoder

    # --- построение и персистентность -----------------------------------

    @classmethod
    def build(cls, chunks: list[Chunk], encoder: Encoder | None = None) -> HybridRetriever:
        encoder = encoder or _default_encoder()
        embeddings = encoder([c.text for c in chunks], False)
        return cls(chunks, embeddings=embeddings, encoder=encoder)

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
        if self._embeddings is not None:
            np.save(index_dir / "embeddings.npy", self._embeddings)
        meta = {
            "model": DENSE_MODEL,
            "n_chunks": len(self.chunks),
            "dense": self._embeddings is not None,
        }
        (index_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, index_dir: Path, encoder: Encoder | None = None) -> HybridRetriever:
        chunks = [
            Chunk.from_dict(json.loads(line))
            for line in (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        emb_path = index_dir / "embeddings.npy"
        embeddings = np.load(emb_path) if emb_path.exists() else None
        return cls(chunks, embeddings=embeddings, encoder=encoder)

    # --- поиск ------------------------------------------------------------

    def search(
        self, query: str, k: int = 8, rrf_k: int = 60, book: str | None = None
    ) -> list[Chunk]:
        rank_lists = [self._rank_bm25(query)]
        if self._embeddings is not None:
            rank_lists.append(self._rank_dense(query))
        scores: dict[int, float] = {}
        for rank_list in rank_lists:
            for rank, idx in enumerate(rank_list):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        order = sorted(scores, key=scores.get, reverse=True)
        if book is not None:
            order = [i for i in order if self.chunks[i].book == book]
        return [self.chunks[i] for i in order[:k]]

    def book_slice(self, book: str, where: str, k: int) -> list[Chunk]:
        """Голова ('head') или хвост ('tail') книги в порядке повествования.

        Опирается на то, что build_index пишет чанки последовательно
        по тексту — порядок в chunks.jsonl и есть порядок повествования.
        """
        ids = [i for i, c in enumerate(self.chunks) if c.book == book]
        picked = ids[:k] if where == "head" else ids[-k:]
        return [self.chunks[i] for i in picked]

    def _rank_bm25(self, query: str, depth: int = 50) -> list[int]:
        scores = self._bm25.get_scores(bm25_tokens(query))
        return sorted(range(len(scores)), key=scores.__getitem__, reverse=True)[:depth]

    def _rank_dense(self, query: str, depth: int = 50) -> list[int]:
        if self._encoder is None:
            self._encoder = _default_encoder()
        q = self._encoder([query], True)
        sims = (self._embeddings @ q.T).ravel()
        return sorted(range(len(sims)), key=sims.__getitem__, reverse=True)[:depth]
