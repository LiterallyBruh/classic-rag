"""Reranker: cross-encoder поверх кандидатов гибридного поиска.

Зачем второй этап (аргументация для защиты): bi-encoder (e5) и BM25 оценивают
запрос и текст независимо — быстро, но грубо. Cross-encoder читает пару
(запрос, чанк) целиком и точнее ранжирует голову выдачи. Схема
«дёшево отобрать N=30 → дорого переранжировать → top-k» — стандартный
компромисс качество/латентность.

Модель: BAAI/bge-reranker-v2-m3 — мультиязычный SOTA среди открытых
реранкеров разумного размера (~0.6B), русский поддерживает.
Загружается лениво; в тестах скорер инъецируется.
"""

from __future__ import annotations

from collections.abc import Callable

from .chunking import Chunk

RERANK_MODEL = "BAAI/bge-reranker-v2-m3"

# (запрос, тексты) -> релевантности той же длины
Scorer = Callable[[str, list[str]], list[float]]


def _default_scorer() -> Scorer:
    from sentence_transformers import CrossEncoder  # тяжёлый импорт — лениво

    # max_length ограничивает память: чанки-«главы» достигают 15 тыс. слов,
    # без лимита внимание на 30 парах выедает всю память GPU/MPS.
    model = CrossEncoder(RERANK_MODEL, max_length=1024)

    def score(query: str, texts: list[str]) -> list[float]:
        return model.predict([(query, t) for t in texts], batch_size=8).tolist()

    return score


class Reranker:
    def __init__(self, scorer: Scorer | None = None) -> None:
        self._scorer = scorer

    def rerank(self, query: str, chunks: list[Chunk], k: int = 6) -> list[Chunk]:
        if not chunks:
            return []
        if self._scorer is None:
            self._scorer = _default_scorer()
        scores = self._scorer(query, [c.text for c in chunks])
        order = sorted(range(len(chunks)), key=scores.__getitem__, reverse=True)
        return [chunks[i] for i in order[:k]]
