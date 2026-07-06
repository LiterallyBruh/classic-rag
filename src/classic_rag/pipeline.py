"""Сквозной пайплайн: нормализация имён → гибридный поиск → reranker → генерация.

Параметры этапов (см. docs/decisions.md, D-008):
- retrieve_k=30: широкая сетка для реранкера — RRF-голова достаточно шумная,
  чтобы правильный чанк был в топ-30, но не всегда в топ-5;
- final_k=6: столько фрагментов идёт в контекст LLM (~1200 слов).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .chunking import Chunk
from .generate import answer
from .normalize import CharacterNormalizer
from .rerank import Reranker
from .retrieval import HybridRetriever

DEFAULT_INDEX = Path("data/index/window")


@dataclass
class RagResult:
    query: str
    answer: str
    chunks: list[Chunk] = field(default_factory=list)


class RagPipeline:
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: Reranker | None = None,
        normalizer: CharacterNormalizer | None = None,
        retrieve_k: int = 30,
        final_k: int = 6,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker or Reranker()
        self.normalizer = normalizer or CharacterNormalizer()
        self.retrieve_k = retrieve_k
        self.final_k = final_k

    @classmethod
    def from_index(cls, index_dir: Path = DEFAULT_INDEX, **kwargs) -> RagPipeline:
        return cls(HybridRetriever.load(index_dir), **kwargs)

    def retrieve(self, query: str, book: str | None = None) -> list[Chunk]:
        expanded = self.normalizer.expand_query(query, book=book)
        candidates = self.retriever.search(expanded, k=self.retrieve_k, book=book)
        # реранкеру отдаём исходный запрос: алиасное расширение помогает
        # recall'у BM25/e5, а cross-encoder точнее судит по живой формулировке
        return self.reranker.rerank(query, candidates, k=self.final_k)

    def ask(self, query: str, book: str | None = None, llm_client=None) -> RagResult:
        chunks = self.retrieve(query, book=book)
        reply = answer(query, chunks, client=llm_client)
        return RagResult(query=query, answer=reply, chunks=chunks)
