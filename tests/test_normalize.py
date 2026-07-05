from pathlib import Path

from classic_rag.normalize import CharacterNormalizer


def norm() -> CharacterNormalizer:
    return CharacterNormalizer(Path("configs/characters.yaml"))


def test_alias_expansion():
    q = norm().expand_query("почему Родя убил старуху")
    assert "Раскольников" in q


def test_no_alias_no_change():
    q = "какая погода сегодня"
    assert norm().expand_query(q) == q


def test_book_filter():
    q = norm().expand_query("что сделал князь", book="idiot")
    assert "Мышкин" in q
