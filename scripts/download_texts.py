"""Загрузка текстов корпуса из открытых источников.

Все четыре произведения — в общественном достоянии:
Достоевский умер в 1881, Холодковский (переводчик «Фауста») — в 1921.

Запускать локально: python scripts/download_texts.py
Скрипт сохраняет сырые HTML/TXT в data/raw/, дальнейшая очистка —
в scripts/clean_texts.py.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

RAW_DIR = Path("data/raw")

# Источники: библиотека Мошкова (az.lib.ru) и ilibrary.ru — открытые
# электронные библиотеки текстов в общественном достоянии.
# При необходимости замените URL на альтернативные зеркала.
SOURCES: dict[str, str] = {
    "prestuplenie_i_nakazanie": "http://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml",
    "idiot": "http://az.lib.ru/d/dostoewskij_f_m/text_0070.shtml",
    "besy": "http://az.lib.ru/d/dostoewskij_f_m/text_0080.shtml",
    # Фауст в переводе Н. А. Холодковского, 1878 (перевод в общественном
    # достоянии). Проверено по индексу http://az.lib.ru/g/gete_i_w/:
    # это издание 533k, "Перевод Н. А. Холодковского".
    "faust_holodkovsky": "http://az.lib.ru/g/gete_i_w/text_1800_faust.shtml",
}

HEADERS = {"User-Agent": "ClassicLiteratureRAG research project (educational, non-commercial)"}

# Ожидаемый минимальный размер HTML (байт) — грубая защита от заглушек/обрывов.
# Реальные размеры по az.lib.ru: ПиН 1242k, Идиот 1517k, Бесы ~1500k, Фауст 533k.
MIN_SIZE: dict[str, int] = {
    "prestuplenie_i_nakazanie": 1_000_000,
    "idiot": 1_200_000,
    "besy": 1_200_000,
    "faust_holodkovsky": 400_000,
}


def download(name: str, url: str) -> None:
    out = RAW_DIR / f"{name}.html"
    if out.exists():
        print(f"[skip] {name} уже загружен")
        return
    print(f"[get ] {name} <- {url}")
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding  # az.lib.ru отдаёт koi8-r/cp1251
    size = len(resp.text.encode("utf-8"))
    if size < MIN_SIZE.get(name, 0):
        raise RuntimeError(
            f"{name}: получено {size} байт, ожидалось >= {MIN_SIZE[name]}. "
            "Похоже на заглушку/обрыв — файл не сохранён."
        )
    out.write_text(resp.text, encoding="utf-8")
    time.sleep(2)  # вежливая пауза между запросами


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        download(name, url)
    print("Готово. Проверьте файлы в data/raw/ и запустите clean_texts.py")


if __name__ == "__main__":
    main()
