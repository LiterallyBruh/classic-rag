"""Нормализация имён персонажей в запросах.

Проблема: пользователь спрашивает «почему Родя убил старуху», а в тексте
чаще «Раскольников». Расширение запроса каноническим именем и алиасами
заметно поднимает recall (метрики до/после — в eval/report.md).

Известная сложность (честно обсуждаем на защите): омонимия
(Верховенский отец/сын в «Бесах») — решается контекстными правилами
или уточняющим вопросом пользователю.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class CharacterNormalizer:
    def __init__(self, config_path: Path = Path("configs/characters.yaml")) -> None:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        # alias(lower) -> (book, canonical)
        self._alias_map: dict[str, list[tuple[str, str]]] = {}
        for book, chars in raw.items():
            for canonical, aliases in chars.items():
                for name in [canonical, *aliases]:
                    self._alias_map.setdefault(name.lower(), []).append((book, canonical))

    def expand_query(self, query: str, book: str | None = None) -> str:
        """Добавляет к запросу канонические имена найденных алиасов."""
        additions: set[str] = set()
        q_lower = query.lower()
        for alias, targets in self._alias_map.items():
            if alias in q_lower:
                for target_book, canonical in targets:
                    if book is None or target_book == book:
                        additions.add(canonical)
        if not additions:
            return query
        return f"{query} ({' '.join(sorted(additions))})"
