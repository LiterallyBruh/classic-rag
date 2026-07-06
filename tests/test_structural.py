"""Тесты структурных (позиционных) вопросов: интент, срез книги, маршрутизация."""

import numpy as np

from classic_rag.chunking import Chunk
from classic_rag.pipeline import RagPipeline
from classic_rag.rerank import Reranker
from classic_rag.retrieval import HybridRetriever
from classic_rag.structural import positional_intent, resolve_book

# --- интент ---------------------------------------------------------------


def test_tail_intent() -> None:
    assert positional_intent("Последняя фраза Мышкина в произведении Идиот") == "tail"
    assert positional_intent("Чем заканчивается роман?") == "tail"
    assert positional_intent("Какова развязка?") == "tail"
    assert positional_intent("Что происходит в конце романа?") == "tail"


def test_head_intent() -> None:
    assert positional_intent("Первая фраза романа «Идиот»") == "head"
    assert positional_intent("С чего начинается «Фауст»?") == "head"
    assert positional_intent("Что происходит в начале романа?") == "head"


def test_no_intent_on_content_questions() -> None:
    assert positional_intent("Почему Раскольников признался Соне?") is None
    assert positional_intent("Кто первый заговорил с князем в поезде?") is None
    assert positional_intent("Что было в конце пятой главы?") is None
    # «последний разговор/встреча» — контентные вопросы: сцена не обязана
    # быть в хвосте книги
    assert positional_intent("Что Порфирий советовал при последнем разговоре?") is None
    assert positional_intent("Что сделала Дуня при последней встрече со Свидригайловым?") is None


def test_resolve_book() -> None:
    assert resolve_book("Последняя фраза Мышкина в произведении Идиот") == "idiot"
    assert resolve_book("Чем заканчивается «Фауст»?") == "faust_holodkovsky"
    assert resolve_book("Чем заканчивается роман?") is None
    assert resolve_book("Идиот или Бесы — где больше персонажей?") is None  # двусмысленно


# --- срез книги и маршрутизация -------------------------------------------


def book_chunks() -> list[Chunk]:
    other = [Chunk(book="besy", text=f"бесы {i}", strategy="window") for i in range(3)]
    idiot = [
        Chunk(book="idiot", text=f"идиот глава {i}: князь Мышкин", strategy="window",
              part="1", chapter=str(i))
        for i in range(1, 7)
    ]
    return other + idiot  # порядок в списке = порядок повествования


def constant_scorer(query: str, texts: list[str]) -> list[float]:
    return [1.0] * len(texts)


def fake_encoder(texts: list[str], is_query: bool) -> np.ndarray:
    out = np.ones((len(texts), 4), dtype=np.float32)
    return out / 2.0


def test_book_slice_head_and_tail() -> None:
    r = HybridRetriever(book_chunks(), encoder=fake_encoder)
    head = r.book_slice("idiot", "head", 2)
    tail = r.book_slice("idiot", "tail", 2)
    assert [c.chapter for c in head] == ["1", "2"]
    assert [c.chapter for c in tail] == ["5", "6"]


def test_pipeline_routes_tail_in_story_order() -> None:
    chunks = book_chunks()
    retriever = HybridRetriever(
        chunks, embeddings=fake_encoder([c.text for c in chunks], False), encoder=fake_encoder
    )
    pipeline = RagPipeline(
        retriever, reranker=Reranker(scorer=constant_scorer), retrieve_k=4, final_k=3
    )
    got = pipeline.retrieve("Последняя фраза Мышкина в произведении Идиот")
    # только «Идиот», только хвост (retrieve_k=4 последних глав из 6),
    # порядок повествования сохранён
    chapters = [int(c.chapter) for c in got]
    assert all(c.book == "idiot" for c in got)
    assert set(chapters) <= {3, 4, 5, 6}
    assert chapters == sorted(chapters)
