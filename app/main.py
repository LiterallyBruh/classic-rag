"""Streamlit-демо ClassicRAG.

Работает и без LLM-ключа: тогда показывает найденные фрагменты с адресами,
а генерация ответа отключена (полезно для проверки retrieval и деплоя
без секретов).
"""

import streamlit as st
from dotenv import load_dotenv

from classic_rag.feedback import save_feedback
from classic_rag.llm import llm_configured
from classic_rag.pipeline import DEFAULT_INDEX, RagPipeline

load_dotenv()  # локальный запуск без docker: ключи из .env

BOOKS = {
    "Все книги": None,
    "Преступление и наказание": "prestuplenie_i_nakazanie",
    "Идиот": "idiot",
    "Бесы": "besy",
    "Фауст (пер. Холодковского)": "faust_holodkovsky",
}

EXAMPLES = [
    "Почему Раскольников признался Соне?",
    "Что Мефистофель говорит о теории?",
    "Кто такая Хромоножка?",
    "Правда ли, что «красота спасёт мир» — слова Мышкина?",
]

st.set_page_config(page_title="ClassicRAG", page_icon="📚")
st.title("📚 ClassicRAG")
st.caption("Ответы по тексту классики — с цитатами и указанием главы. Без выдумок.")


@st.cache_resource(show_spinner="Загружаю индекс и модели (первый запуск — до минуты)...")
def load_pipeline() -> RagPipeline:
    if not (DEFAULT_INDEX / "chunks.jsonl").exists():
        st.error(
            "Индекс не найден. Постройте его: `python scripts/bootstrap.py` "
            "(скачает тексты и создаст data/index/window)."
        )
        st.stop()
    return RagPipeline.from_index()


with st.sidebar:
    book_label = st.selectbox("Произведение", list(BOOKS))
    st.markdown("**Примеры вопросов**")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state["query"] = ex
    if not llm_configured():
        st.info(
            "LLM-ключ не задан (.env) — показываю только найденные "
            "фрагменты, без генерации ответа."
        )

query = st.text_input(
    "Вопрос", key="query", placeholder="Почему Родя признался Соне?"
)

if query:
    pipeline = load_pipeline()
    # ответ кэшируется в сессии: клики по кнопкам фидбека перезапускают
    # скрипт, и без кэша каждый клик заново гонял бы retrieval и LLM
    if st.session_state.get("last_key") != (query, book_label):
        if llm_configured():
            with st.spinner("Ищу в тексте и формулирую ответ..."):
                result = pipeline.ask(query, book=BOOKS[book_label])
            answer, chunks = result.answer, result.chunks
        else:
            with st.spinner("Ищу в тексте..."):
                answer, chunks = None, pipeline.retrieve(query, book=BOOKS[book_label])
        st.session_state.update(
            last_key=(query, book_label), last_answer=answer,
            last_chunks=chunks, feedback_sent=False,
        )
    answer, chunks = st.session_state["last_answer"], st.session_state["last_chunks"]
    if answer:
        st.markdown(answer)
    st.subheader("Найденные фрагменты")
    for c in chunks:
        with st.expander(c.citation):
            st.markdown(c.text)

    if st.session_state.get("feedback_sent"):
        st.success("Спасибо! Отзыв записан.")
    else:
        with st.form("feedback_form", border=False):
            col_rate, col_comment = st.columns([1, 3])
            rating = col_rate.radio(
                "Ответ помог?", ["👍 Да", "👎 Нет"], horizontal=True
            )
            comment = col_comment.text_input(
                "Комментарий (необязательно)", placeholder="Что не так или чего не хватило?"
            )
            if st.form_submit_button("Отправить отзыв"):
                save_feedback({
                    "query": query,
                    "book": BOOKS[book_label],
                    "answer": answer,
                    "citations": [c.citation for c in chunks],
                    "rating": "up" if rating.startswith("👍") else "down",
                    "comment": comment.strip(),
                })
                st.session_state["feedback_sent"] = True
                st.rerun()

st.divider()
st.caption(
    "Корпус: Достоевский («Преступление и наказание», «Идиот», «Бесы») и "
    "«Фауст» в переводе Н. Холодковского — тексты в общественном достоянии. "
    "Ассистент отвечает только по первоисточнику и отказывается, если ответа "
    "в тексте нет."
)
