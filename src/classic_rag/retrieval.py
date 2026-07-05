"""Гибридный retrieval: BM25 + dense-эмбеддинги, слияние через RRF.

Дизайн-решения (аргументация для защиты):
- BM25 ловит точные редкие термины (имена, топонимы), dense — перефразировки
  и интерпретационные вопросы; по литературным текстам ни один из них
  не доминирует, поэтому гибрид (см. eval/report.md, таблица сравнения).
- RRF (reciprocal rank fusion) выбран вместо взвешенной суммы score'ов,
  потому что не требует калибровки шкал между BM25 и косинусной близостью.
"""

from __future__ import annotations

from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

DENSE_MODEL = "intfloat/multilingual-e5-base"


@dataclass
class Chunk:
    book: str
    part: str
    chapter: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.book}, часть {self.part}, глава {self.chapter}"


class HybridRetriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self._bm25 = BM25Okapi([c.text.lower().split() for c in chunks])
        self._encoder = SentenceTransformer(DENSE_MODEL)
        self._embeddings = self._encoder.encode(
            [f"passage: {c.text}" for c in chunks],  # префикс требуется e5
            normalize_embeddings=True,
            show_progress_bar=True,
        )

    def search(self, query: str, k: int = 8, rrf_k: int = 60) -> list[Chunk]:
        bm25_rank = self._rank_bm25(query)
        dense_rank = self._rank_dense(query)
        scores: dict[int, float] = {}
        for rank_list in (bm25_rank, dense_rank):
            for rank, idx in enumerate(rank_list):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        top = sorted(scores, key=scores.get, reverse=True)[:k]
        return [self.chunks[i] for i in top]

    def _rank_bm25(self, query: str, depth: int = 50) -> list[int]:
        scores = self._bm25.get_scores(query.lower().split())
        return sorted(range(len(scores)), key=scores.__getitem__, reverse=True)[:depth]

    def _rank_dense(self, query: str, depth: int = 50) -> list[int]:
        q = self._encoder.encode([f"query: {query}"], normalize_embeddings=True)
        sims = (self._embeddings @ q.T).ravel()
        return sorted(range(len(sims)), key=sims.__getitem__, reverse=True)[:depth]
