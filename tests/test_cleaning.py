"""Тесты парсеров корпуса: хелперы номеров и мини-HTML в формате az.lib.ru."""

from classic_rag.cleaning import ordinal_to_int, parse_faust, parse_novel, roman_to_int

# --- Хелперы -----------------------------------------------------------------


def test_ordinal_to_int() -> None:
    assert ordinal_to_int("первая") == 1
    assert ordinal_to_int("ПЯТАЯ") == 5
    assert ordinal_to_int("девятая") == 9
    assert ordinal_to_int("вступление") is None


def test_roman_to_int() -> None:
    assert roman_to_int("IV") == 4
    assert roman_to_int("XVI") == 16
    # Кириллическая Х из OCR и разорванный жирный шрифт («XII I» из <b>XII</b><b>I</b>)
    assert roman_to_int("ХI") == 11
    assert roman_to_int("XII I") == 13
    assert roman_to_int("Глава") is None
    assert roman_to_int("") is None


# --- Романы ------------------------------------------------------------------

NOVEL_HTML = """
<div align="center" ><p >Часть первая</p></div>
<dd>&nbsp;&nbsp; Глава первая. Пункт оглавления — должен быть отброшен
<h4><div align="center" ><p ><b>Часть первая</b></p></div></h4>
<h4><div align="center" ><p ><b>I</b></p></div></h4>
<dd>&nbsp;&nbsp; Первый абзац первой главы.
<dd>&nbsp;&nbsp; Второй абзац <i>с курсивом</i> внутри.
<h4><div align="center" ><p ><b>II</b></p></div></h4>
<dd>&nbsp;&nbsp; Абзац второй главы.
<h4><div align="center" ><p ><b>ЧАСТЬ ВТОРАЯ</b></p></div></h4>
<h4><div align="center" ><p ><b>I</b></p></div></h4>
<dd>&nbsp;&nbsp; Часть вторая, глава один.
<dd>&nbsp;&nbsp; <i>Оригинал здесь: Библиотека</i>.
<dd>&nbsp;&nbsp; Мусор после футера.
"""


def test_parse_novel_structure() -> None:
    recs = parse_novel(NOVEL_HTML, "test")
    assert [r["text"] for r in recs] == [
        "Первый абзац первой главы.",
        "Второй абзац с курсивом внутри.",
        "Абзац второй главы.",
        "Часть вторая, глава один.",
    ]
    assert [(r["part"], r["chapter"]) for r in recs] == [
        ("1", "1"),
        ("1", "1"),
        ("1", "2"),
        ("2", "1"),
    ]


NAMED_CHAPTERS_HTML = """
<h4><div align="center" ><p ><b>Часть первая</b></p></div></h4>
<div align="center" ><p >Глава первая<br>Ночь</p></div>
<div align="center" ><p >I</p></div>
<dd>&nbsp;&nbsp; Абзац раздела один.
<div align="center" ><p >II</p></div>
<dd>&nbsp;&nbsp; Абзац раздела два.
<div align="center" ><p >Глава вторая<br>Поединок</p></div>
<dd>&nbsp;&nbsp; Абзац второй главы.
"""


def test_parse_novel_named_chapters_with_sections() -> None:
    recs = parse_novel(NAMED_CHAPTERS_HTML, "test")
    assert [(r["chapter"], r["chapter_title"], r["section"]) for r in recs] == [
        ("1", "Ночь", "1"),
        ("1", "Ночь", "2"),
        ("2", "Поединок", None),
    ]


# --- «Фауст» -----------------------------------------------------------------

FAUST_HTML = """
<dd>&nbsp;&nbsp;  (перевод с нем. Н.Холодковского)
<dd>&nbsp;&nbsp;          ПРОЛОГ НА НЕБЕСАХ
<dd>&nbsp;&nbsp;
<dd>&nbsp;&nbsp;            Рафаил
<dd>&nbsp;&nbsp;
<dd>&nbsp;&nbsp;    Звуча в гармонии вселенной
<dd>&nbsp;&nbsp;    И в хоре сфер гремя, как гром.
<dd>&nbsp;&nbsp;          * ЧАСТЬ ПЕРВАЯ *
<dd>&nbsp;&nbsp;          НОЧЬ
<dd>&nbsp;&nbsp;            Фауст
<dd>&nbsp;&nbsp;            (входит)
<dd>&nbsp;&nbsp;    Я философию постиг,
<dd>&nbsp;&nbsp;    Я стал юристом, стал врачом...
<dd>&nbsp;&nbsp;          ПРИМЕЧАНИЯ:
<dd>&nbsp;&nbsp;    Комментарий издания, не текст Гёте.
"""


def test_parse_faust() -> None:
    recs = parse_faust(FAUST_HTML, "faust")
    assert len(recs) == 2
    prolog, night = recs
    # Пролог — до «* ЧАСТЬ ПЕРВАЯ *», вне частей
    assert prolog["part"] is None
    assert prolog["scene"] == "ПРОЛОГ НА НЕБЕСАХ"
    assert prolog["speaker"] == "Рафаил"
    assert prolog["text"] == "Звуча в гармонии вселенной\nИ в хоре сфер гремя, как гром."
    # Сцена первой части; центрированная ремарка вошла в реплику
    assert night["part"] == "1"
    assert night["scene"] == "НОЧЬ"
    assert night["speaker"] == "Фауст"
    assert night["text"].startswith("(входит)")
    # Примечания издания отрезаны
    assert all("Комментарий" not in r["text"] for r in recs)
