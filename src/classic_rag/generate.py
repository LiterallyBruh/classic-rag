"""Генерация ответа строго по найденным фрагментам.

Ключевое продуктовое отличие от «просто спросить ChatGPT»:
1) модель обязана цитировать фрагменты и указывать часть/главу;
2) если фрагменты не содержат ответа — система отвечает
   «в тексте не нашёл», а не сочиняет.
"""

from __future__ import annotations

import os

from openai import OpenAI

from .retrieval import Chunk

SYSTEM_PROMPT = """Ты — ассистент по классической литературе.
Отвечай ТОЛЬКО на основе приведённых фрагментов текста.
Правила:
1. Каждое утверждение подкрепляй короткой цитатой из фрагмента
   и ссылкой вида [часть N, глава M].
2. Если фрагменты не содержат ответа, скажи ровно:
   «В предоставленных фрагментах текста ответа нет.»
3. Не используй знания о произведении помимо фрагментов.
4. Цитаты — не длиннее одного предложения."""


def build_context(chunks: list[Chunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[Фрагмент {i}] ({c.citation})\n{c.text}")
    return "\n\n".join(blocks)


def answer(query: str, chunks: list[Chunk], model: str | None = None) -> str:
    client = OpenAI(  # совместимо с любым OpenAI-compatible эндпоинтом
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )
    resp = client.chat.completions.create(
        model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{build_context(chunks)}\n\nВопрос: {query}"},
        ],
    )
    return resp.choices[0].message.content or ""
