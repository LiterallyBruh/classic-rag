"""Streamlit-демо ClassicRAG."""

import json
from pathlib import Path

import streamlit as st

from classic_rag.generate import answer
from classic_rag.normalize import CharacterNormalizer
from classic_rag.retrieval import Chunk, HybridRetriever

BOOKS = {
    "Преступление и наказание": "prestuplenie_i_nakazanie",
    "Идиот": "idiot",
    "Бесы": "besy",
    "Фауст (пер. Холодковского)": "faust_holodkovsky",
    "Все книги": None,
}

st.set_page_config(page_title="ClassicRAG", page_icon="📚")
st.title("📚 ClassicRAG")
st.caption("Ответы по тексту классики — с цитатами и указанием главы. Без выдумок.")


@st.cache_resource
def load_retriever() -> HybridRetriever:
    chunks: list[Chunk] = []
    for path in Path("data/processed").glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                chunks.append(Chunk(r["book"], r["part"], r["chapter"], r["text"]))
    return HybridRetriever(chunks)


book_label = st.selectbox("Произведение", list(BOOKS))
query = st.text_input("Вопрос", placeholder="Почему Родя признался Соне?")

if query:
    retriever = load_retriever()
    normalizer = CharacterNormalizer()
    expanded = normalizer.expand_query(query, book=BOOKS[book_label])
    chunks = retriever.search(expanded, k=8)
    if BOOKS[book_label]:
        chunks = [c for c in chunks if c.book == BOOKS[book_label]] or chunks
    with st.spinner("Ищу в тексте..."):
        result = answer(query, chunks)
    st.markdown(result)
    with st.expander("Найденные фрагменты"):
        for c in chunks:
            st.markdown(f"**{c.citation}**\n\n{c.text[:600]}…")
