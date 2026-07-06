"""Тесты реранкера, генерации и сквозного пайплайна — с фейками, без сети."""

from pathlib import Path

import numpy as np

from classic_rag.chunking import Chunk
from classic_rag.generate import REFUSAL, answer, build_context
from classic_rag.normalize import CharacterNormalizer
from classic_rag.pipeline import RagPipeline
from classic_rag.rerank import Reranker
from classic_rag.retrieval import HybridRetriever


def make_chunks() -> list[Chunk]:
    texts = [
        "Раскольников спрятал топор под пальто и пошёл к старухе.",
        "Соня читала книгу и вязала у окна.",
        "Он поднялся по лестнице тихо, топор оттягивал руку.",
    ]
    return [Chunk(book="prestuplenie_i_nakazanie", text=t, strategy="window",
                  part="1", chapter=str(i)) for i, t in enumerate(texts, 1)]


def overlap_scorer(query: str, texts: list[str]) -> list[float]:
    q = set(query.lower().split())
    return [len(q & set(t.lower().split())) / (len(q) or 1) for t in texts]


# --- reranker ------------------------------------------------------------------


def test_reranker_orders_by_score() -> None:
    chunks = make_chunks()
    top = Reranker(scorer=overlap_scorer).rerank("топор оттягивал руку", chunks, k=2)
    assert top[0].text.startswith("Он поднялся")
    assert len(top) == 2


def test_reranker_empty_input() -> None:
    assert Reranker(scorer=overlap_scorer).rerank("вопрос", [], k=3) == []


# --- генерация -----------------------------------------------------------------


class FakeLLM:
    """Минимальный OpenAI-совместимый клиент, возвращающий заготовку."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.last_messages: list[dict] | None = None
        outer = self

        class _Completions:
            @staticmethod
            def create(**kwargs):
                outer.last_messages = kwargs["messages"]

                class _Msg:
                    content = outer.reply

                class _Choice:
                    message = _Msg()

                class _Resp:
                    choices = [_Choice()]

                return _Resp()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def test_build_context_contains_citations() -> None:
    ctx = build_context(make_chunks())
    assert "[Фрагмент 1]" in ctx
    assert "Преступление и наказание, часть 1, глава 1" in ctx


def test_answer_uses_injected_client() -> None:
    llm = FakeLLM("Ответ с цитатой (Преступление и наказание, часть 1, глава 1).")
    result = answer("вопрос", make_chunks(), client=llm)
    assert "часть 1, глава 1" in result
    # контекст и вопрос дошли до модели
    user_msg = llm.last_messages[-1]["content"]
    assert "топор под пальто" in user_msg and "вопрос" in user_msg


def test_answer_refuses_without_chunks() -> None:
    assert answer("вопрос", []) == REFUSAL


# --- сквозной пайплайн ----------------------------------------------------------


def fake_encoder(texts: list[str], is_query: bool) -> np.ndarray:
    vocab = ["топор", "старуха", "лестница", "соня"]
    out = np.zeros((len(texts), len(vocab)), dtype=np.float32)
    for i, t in enumerate(texts):
        for j, w in enumerate(vocab):
            out[i, j] = float(w in t.lower())
        out[i] /= np.linalg.norm(out[i]) or 1.0
    return out


def test_pipeline_end_to_end(tmp_path: Path) -> None:
    chunks = make_chunks()
    retriever = HybridRetriever(
        chunks, embeddings=fake_encoder([c.text for c in chunks], False), encoder=fake_encoder
    )
    pipeline = RagPipeline(
        retriever,
        reranker=Reranker(scorer=overlap_scorer),
        normalizer=CharacterNormalizer(Path("configs/characters.yaml")),
        retrieve_k=3,
        final_k=2,
    )
    result = pipeline.ask("где Родя спрятал топор", llm_client=FakeLLM("ок"))
    assert result.answer == "ок"
    assert len(result.chunks) == 2
    # нормализация сработала: «Родя» расширился до «Раскольников», чанк найден
    assert any("Раскольников" in c.text for c in result.chunks)
