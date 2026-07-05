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
    # Фауст в переводе Н. А. Холодковского (пер. в общественном достоянии)
    "faust_holodkovsky": "http://az.lib.ru/g/gete_i_w/text_0030.shtml",
}

HEADERS = {"User-Agent": "ClassicRAG research project (educational, non-commercial)"}


def download(name: str, url: str) -> None:
    out = RAW_DIR / f"{name}.html"
    if out.exists():
        print(f"[skip] {name} уже загружен")
        return
    print(f"[get ] {name} <- {url}")
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding  # az.lib.ru отдаёт koi8-r/cp1251
    out.write_text(resp.text, encoding="utf-8")
    time.sleep(2)  # вежливая пауза между запросами


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        download(name, url)
    print("Готово. Проверьте файлы в data/raw/ и запустите clean_texts.py")


if __name__ == "__main__":
    main()
