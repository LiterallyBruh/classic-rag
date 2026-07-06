"""Очистка HTML az.lib.ru и структурная разметка корпуса.

Два формата на входе (см. docs/decisions.md, D-002):

1. Романы Достоевского: каждый абзац — одна строка ``<dd>&nbsp;&nbsp; текст``,
   заголовки — блоки ``<div align="center">``. Настоящие заголовки частей
   выделены ``<b>``, а пункты авторского оглавления — нет; по этому признаку
   оглавление отбрасывается.
2. «Фауст» — préformatted-текст, каждая строка стиха в своём ``<dd>``.
   Уровень отступа различает стих (~4 пробела), заголовок сцены
   (КАПС, ~10 пробелов) и имя говорящего (~12 пробелов, смешанный регистр).

Единица выхода: для романов — абзац с адресом (часть, глава, раздел),
для «Фауста» — реплика с адресом (часть, сцена, говорящий).
Адрес — основа точного цитирования в ответах ассистента.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import asdict, dataclass

# --- Нормализация номеров ---------------------------------------------------

_ORDINALS = {
    "первая": 1,
    "вторая": 2,
    "третья": 3,
    "четвертая": 4,
    "четвёртая": 4,
    "пятая": 5,
    "шестая": 6,
    "седьмая": 7,
    "восьмая": 8,
    "девятая": 9,
    "десятая": 10,
}

# OCR-тексты смешивают латиницу и кириллицу в римских цифрах (Х вместо X).
_CYR_TO_LAT = str.maketrans("ХСІМ", "XCIM")
_ROMAN_RE = re.compile(r"^[IVXLC]+$")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def ordinal_to_int(word: str) -> int | None:
    """«первая»/«ПЕРВАЯ» -> 1; None, если слово не порядковое числительное."""
    return _ORDINALS.get(word.strip().casefold())


def roman_to_int(s: str) -> int | None:
    """Римская цифра (в т.ч. с кириллическими Х/С) -> int; иначе None.

    Внутренние пробелы игнорируются: в вёрстке встречается разорванный
    жирный шрифт вида ``<b>XII</b><b>I</b>``, дающий после очистки «XII I».
    """
    s = re.sub(r"\s+", "", s).translate(_CYR_TO_LAT).upper()
    if not _ROMAN_RE.match(s):
        return None
    total = 0
    for cur, nxt in zip(s, s[1:] + " ", strict=True):
        v = _ROMAN_VALUES[cur]
        total += -v if _ROMAN_VALUES.get(nxt, 0) > v else v
    return total


def _clean_text(s: str) -> str:
    s = html_lib.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", s).strip()


# --- Романы Достоевского -----------------------------------------------------

@dataclass
class Record:
    book: str
    part: str | None
    chapter: str | None
    chapter_title: str | None
    section: str | None
    scene: str | None
    speaker: str | None
    para_id: int
    text: str


_PART_RE = re.compile(r"^часть\s+(\w+)", re.I)
_CHAPTER_RE = re.compile(r"^глава\s+(\w+)\s*\.?\s*(.*)", re.I | re.S)
# Заголовки-части без слова «часть»: эпилог и приложение (глава «У Тихона»).
_PART_LABELS = {"эпилог", "приложение"}
_CHAPTER_LABELS = {"заключение", "вместо введения"}
# После этих заголовков идут не тексты романа (черновики, комментарии издания).
_STOP_PREFIXES = ("зависть", "примечания", "комментарии")
# Служебные строки библиотеки в конце файла.
_FOOTER_PREFIXES = ("оригинал здесь",)

_DD_RE = re.compile(r"^<dd>(.*)$", re.I)
_DIV_OPEN_RE = re.compile(r'<div\s+align="?center"?', re.I)


class _NovelState:
    def __init__(self, book: str) -> None:
        self.book = book
        self.part: str | None = None
        self.chapter: str | None = None
        self.chapter_title: str | None = None
        self.section: str | None = None
        # В «Бесах» главы именованные, а римские цифры — подразделы глав;
        # в ПиН/«Идиоте» римские цифры — сами главы.
        self.named_chapters = False
        self.records: list[Record] = []
        self.stopped = False

    def on_header(self, text: str, bold: bool) -> None:
        low = text.casefold()
        # Стоп-маркеры сверяем без пробелов: жирный шрифт в вёрстке бывает
        # разорван («<b>П</b><b>римечания</b>» -> «П римечания»).
        if re.sub(r"\s+", "", low).startswith(_STOP_PREFIXES):
            self.stopped = True
            return
        if m := _PART_RE.match(text):
            # Части оглавления не выделены <b> — пропускаем их.
            if bold and (n := ordinal_to_int(m.group(1))):
                self.part, self.chapter, self.chapter_title, self.section = str(n), None, None, None
            return
        if low in _PART_LABELS:
            # В оглавлении «Бесов» «Приложение» тоже набрано жирным, но
            # настоящий заголовок встречается только после «Части N».
            if bold and self.part is not None:
                self.part = text.capitalize()
                self.chapter = self.chapter_title = self.section = None
            return
        if m := _CHAPTER_RE.match(text):
            if n := ordinal_to_int(m.group(1)):
                self.chapter = str(n)
                self.chapter_title = _clean_text(m.group(2)) or None
                self.section = None
                self.named_chapters = True
            return
        if (n := roman_to_int(text)) is not None:
            if self.named_chapters:
                self.section = str(n)
            else:
                self.chapter, self.chapter_title = str(n), None
            return
        if low in _CHAPTER_LABELS:
            self.chapter, self.chapter_title, self.section = text.capitalize(), None, None
        # Прочие центрированные строки (титул, «* * *») — не структура.

    def on_paragraph(self, text: str) -> None:
        # Всё до первого заголовка части — титул сайта и оглавление.
        if self.part is None or not text:
            return
        # Мини-оглавления внутри текста (напр., в «Приложении» «Бесов»)
        # свёрстаны как обычные <dd>-строки — отбрасываем короткие строки,
        # выглядящие как пункт оглавления.
        low = text.casefold()
        if len(text) < 120 and (_CHAPTER_RE.match(text) or low.startswith(_STOP_PREFIXES)):
            return
        if low.startswith(_FOOTER_PREFIXES):
            self.stopped = True
            return
        self.records.append(
            Record(
                book=self.book,
                part=self.part,
                chapter=self.chapter,
                chapter_title=self.chapter_title,
                section=self.section,
                scene=None,
                speaker=None,
                para_id=len(self.records),
                text=text,
            )
        )


def parse_novel(raw_html: str, book: str) -> list[dict]:
    state = _NovelState(book)
    header_lines: list[str] | None = None  # None = вне заголовочного блока
    header_bold = False

    def close_header() -> None:
        nonlocal header_lines
        text = _clean_text("\n".join(header_lines or []))
        if text:
            state.on_header(text, header_bold)
        header_lines = None

    for line in raw_html.splitlines():
        if state.stopped:
            break
        if m := _DIV_OPEN_RE.search(line):
            header_lines, header_bold = [], "<b>" in line.casefold()
            # Заголовок может целиком помещаться на одной строке.
            rest = line[m.end():]
            rest = rest.split(">", 1)[1] if ">" in rest else ""
            if "</div>" in rest:
                header_lines.append(re.sub(r"<br\s*/?>", ". ", rest.split("</div>")[0], flags=re.I))
                close_header()
            continue
        if header_lines is not None:
            if "</div>" in line:
                close_header()
                continue
            header_bold = header_bold or "<b>" in line.casefold()
            # <br> внутри заголовка отделяет название главы от номера.
            header_lines.append(re.sub(r"<br\s*/?>", ". ", line, flags=re.I))
            continue
        if m := _DD_RE.match(line):
            state.on_paragraph(_clean_text(m.group(1)))
    return [asdict(r) for r in state.records]


# --- «Фауст» (драма) ---------------------------------------------------------

_FAUST_LINE_RE = re.compile(r"^<dd>(.*)$", re.I)
_FAUST_PART_RE = re.compile(r"^\*\s*ЧАСТЬ\s+(\w+)\s*\*$")
# Заголовок/имя — с существенным отступом; стих начинается ближе к краю
# (в источнике: стих 2-6 пробелов, сцена ~12, говорящий ~14).
_HEADER_INDENT = 8
_MAX_SPEAKER_LEN = 50


def _is_caps(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def _is_speaker(s: str) -> bool:
    """Имя говорящего: коротко, с заглавной, без конечной пунктуации.

    Отсекает строки стиха с большим отступом (песни, выравнивание) и
    центрированные ремарки — те начинаются со скобки или кончаются знаком
    препинания («Маргарита под руку с Фаустом,»).
    """
    if not s or s.startswith("(") or len(s) > _MAX_SPEAKER_LEN:
        return False
    if not s[0].isupper() or len(s.split()) > 4:
        return False
    return s[-1] not in ".,:;!?…-"


def parse_faust(raw_html: str, book: str) -> list[dict]:
    records: list[Record] = []
    part: str | None = None
    scene: str | None = None
    speaker: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if buf and scene is not None:
            records.append(
                Record(
                    book=book,
                    part=part,
                    chapter=None,
                    chapter_title=None,
                    section=None,
                    scene=scene,
                    speaker=speaker,
                    para_id=len(records),
                    text="\n".join(buf),
                )
            )
        buf = []

    for raw_line in raw_html.splitlines():
        m = _FAUST_LINE_RE.match(raw_line)
        if not m:
            continue
        line = re.sub(r"<[^>]+>", "", html_lib.unescape(m.group(1))).replace("\xa0", " ")
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if pm := _FAUST_PART_RE.match(stripped):
            flush()
            n = ordinal_to_int(pm.group(1))
            part, scene, speaker = (str(n) if n else pm.group(1)), None, None
            continue
        if indent >= _HEADER_INDENT and _is_caps(stripped):
            if stripped.rstrip(":").casefold() == "примечания":
                break  # дальше — комментарии издания, не текст Гёте
            flush()
            scene, speaker = stripped.rstrip(". "), None
            continue
        if indent >= _HEADER_INDENT and _is_speaker(stripped):
            flush()
            speaker = stripped
            continue
        buf.append(stripped)
    flush()
    return [asdict(r) for r in records]
