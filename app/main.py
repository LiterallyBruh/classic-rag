"""Streamlit-демо ClassicRAG."""

import streamlit as st

from classic_rag.pipeline import RagPipeline

BOOKS = {
    "Все книги": None,
    "Преступление и наказание": "prestuplenie_i_nakazanie",
    "Идиот": "idiot",
    "Бесы": "besy",
    "Фауст (пер. Холодковского)": "faust_holodkovsky",
}

st.set_page_config(page_title="ClassicRAG", page_icon="📚")
st.title("📚 ClassicRAG")
st.caption("Ответы по тексту классики — с цитатами и указанием главы. Без выдумок.")


@st.cache_resource
def load_pipeline() -> RagPipeline:
    return RagPipeline.from_index()


book_label = st.selectbox("Произведение", list(BOOKS))
query = st.text_input("Вопрос", placeholder="Почему Родя признался Соне?")

if query:
    pipeline = load_pipeline()
    with st.spinner("Ищу в тексте..."):
        result = pipeline.ask(query, book=BOOKS[book_label])
    st.markdown(result.answer)
    with st.expander("Найденные фрагменты"):
        for c in result.chunks:
            st.markdown(f"**{c.citation}**\n\n{c.text[:600]}…")
