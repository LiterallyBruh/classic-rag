"""Генерация ответа строго по найденным фрагментам.

Ключевое продуктовое отличие от «просто спросить ChatGPT»:
1) модель обязана цитировать фрагменты и указывать часть/главу;
2) если фрагменты не содержат ответа — система отвечает
   «в тексте не нашёл», а не сочиняет.
"""

from __future__ import annotations

from .chunking import Chunk
from .llm import default_model, make_client

REFUSAL = "В предоставленных фрагментах текста ответа нет."

SYSTEM_PROMPT = f"""Ты — ассистент по классической литературе.
Отвечай ТОЛЬКО на основе приведённых фрагментов текста.
Правила:
1. Каждое утверждение подкрепляй короткой цитатой из фрагмента
   и ссылкой на его адрес в круглых скобках, например
   (Преступление и наказание, часть 5, глава 4).
2. Если фрагменты не содержат ответа, скажи ровно:
   «{REFUSAL}»
3. Не используй знания о произведении помимо фрагментов.
4. Цитаты — не длиннее одного предложения."""


def build_context(chunks: list[Chunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[Фрагмент {i}] ({c.citation})\n{c.text}")
    return "\n\n".join(blocks)


def answer(
    query: str,
    chunks: list[Chunk],
    model: str | None = None,
    client=None,
    note: str | None = None,
) -> str:
    """client — любой OpenAI-совместимый клиент; инъецируется в тестах.

    note — факт о фрагментах, известный пайплайну, но не видный из их текста
    (например, «это самый конец книги» для структурных вопросов, D-011).
    """
    if not chunks:
        return REFUSAL
    if client is None:
        client = make_client()
    prefix = f"{note}\n\n" if note else ""
    resp = client.chat.completions.create(
        model=model or default_model(),
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{prefix}{build_context(chunks)}\n\nВопрос: {query}"},
        ],
    )
    return resp.choices[0].message.content or ""
