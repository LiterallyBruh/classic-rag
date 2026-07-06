"""Тесты стратегий чанкинга и гибридного ретривера (без сети и моделей)."""

import numpy as np

from classic_rag.chunking import Chunk, chunk_records
from classic_rag.retrieval import HybridRetriever


def rec(book="b", part="1", chapter="1", para_id=0, text="", **kw) -> dict:
    return {
        "book": book,
        "part": part,
        "chapter": chapter,
        "chapter_title": kw.get("chapter_title"),
        "section": kw.get("section"),
        "scene": kw.get("scene"),
        "speaker": kw.get("speaker"),
        "para_id": para_id,
        "text": text,
    }


NOVEL = [
    rec(para_id=0, text="один два три"),
    rec(para_id=1, text="четыре пять шесть"),
    rec(para_id=2, chapter="2", text="глава два начинается"),
    rec(para_id=3, chapter="2", text="и продолжается"),
]


def test_paragraph_baseline() -> None:
    chunks = chunk_records(NOVEL, "paragraph")
    assert len(chunks) == 4
    assert chunks[0].text == "один два три"
    assert chunks[2].chapter == "2"


def test_window_respects_chapter_boundary() -> None:
    chunks = chunk_records(NOVEL, "window", target_words=100)
    # главы не смешиваются даже при маленьком корпусе
    assert len(chunks) == 2
    assert chunks[0].text == "один два три\nчетыре пять шесть"
    assert chunks[0].para_ids == [0, 1]
    assert chunks[1].chapter == "2"


def test_window_overlap() -> None:
    recs = [rec(para_id=i, text=f"абзац номер {i} " * 5) for i in range(6)]  # по 15 слов
    chunks = chunk_records(recs, "window", target_words=30)
    assert len(chunks) > 1
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        # перекрытие: последний абзац предыдущего окна открывает следующее
        assert prev.para_ids[-1] == nxt.para_ids[0]


def test_window_splits_long_paragraph() -> None:
    long_text = " ".join(f"Это предложение номер {i}." for i in range(120))  # ~480 слов
    chunks = chunk_records([rec(text=long_text)], "window", target_words=180)
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 250 for c in chunks)


def test_chapter_strategy() -> None:
    chunks = chunk_records(NOVEL, "chapter")
    assert len(chunks) == 2
    assert chunks[0].text == "один два три\nчетыре пять шесть"


def test_faust_speech_units_and_citation() -> None:
    recs = [
        rec(book="faust_holodkovsky", part="1", chapter=None, scene="НОЧЬ",
            speaker="Фауст", para_id=0, text="Я философию постиг"),
        rec(book="faust_holodkovsky", part="1", chapter=None, scene="НОЧЬ",
            speaker="Мефистофель", para_id=1, text="Привет тебе"),
    ]
    chunks = chunk_records(recs, "window", target_words=100)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.text == "Фауст: Я философию постиг\nМефистофель: Привет тебе"
    assert c.speakers == ["Мефистофель", "Фауст"]
    assert c.citation == "Фауст, часть 1, сцена «Ночь»"


def test_novel_citation_with_title() -> None:
    c = Chunk(book="besy", text="т", strategy="window",
              part="2", chapter="1", chapter_title="Ночь", section="3")
    assert c.citation == "Бесы, часть 2, глава 1 «Ночь», раздел 3"


# --- retriever ----------------------------------------------------------------


def fake_encoder(texts: list[str], is_query: bool) -> np.ndarray:
    """Детерминированные «эмбеддинги» по наличию слов — без модели."""
    vocab = ["топор", "старуха", "лестница", "погода"]
    out = np.zeros((len(texts), len(vocab)), dtype=np.float32)
    for i, t in enumerate(texts):
        for j, w in enumerate(vocab):
            out[i, j] = float(w in t.lower())
        norm = np.linalg.norm(out[i]) or 1.0
        out[i] /= norm
    return out


def make_chunks() -> list[Chunk]:
    texts = [
        "Раскольников спрятал топор под пальто и пошёл к старухе.",
        "Соня читала книгу про погоду и вязала.",
        "Он поднялся по лестнице тихо, топор оттягивал руку.",
    ]
    return [Chunk(book="pin", text=t, strategy="paragraph", part="1", chapter=str(i))
            for i, t in enumerate(texts, 1)]


def test_hybrid_search_bm25_only() -> None:
    r = HybridRetriever(make_chunks())
    top = r.search("где Раскольников взял топор", k=2)
    assert top[0].text.startswith("Раскольников")


def test_hybrid_search_with_dense_and_rrf() -> None:
    chunks = make_chunks()
    emb = fake_encoder([c.text for c in chunks], False)
    r = HybridRetriever(chunks, embeddings=emb, encoder=fake_encoder)
    top = r.search("топор старуха", k=2)
    texts = [c.text for c in top]
    assert any("топор под пальто" in t for t in texts)
    assert all("погоду" not in t for t in texts[:1])


def test_save_load_roundtrip(tmp_path) -> None:
    chunks = make_chunks()
    emb = fake_encoder([c.text for c in chunks], False)
    r = HybridRetriever(chunks, embeddings=emb, encoder=fake_encoder)
    r.save(tmp_path)
    r2 = HybridRetriever.load(tmp_path, encoder=fake_encoder)
    assert len(r2.chunks) == 3
    assert r2.search("топор", k=1)[0].text == r.search("топор", k=1)[0].text
