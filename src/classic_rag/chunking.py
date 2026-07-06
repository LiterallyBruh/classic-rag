"""Чанкинг корпуса: три стратегии для сравнения в eval (см. docs/decisions.md, D-006).

1. ``paragraph`` — запись как есть (абзац/реплика). Базлайн: по EDA медиана
   всего ~20 слов — ожидаемо слабый retrieval без контекста.
2. ``window`` — окна с перекрытием: соседние записи склеиваются до целевого
   размера, границы глав/сцен не пересекаются. Сверхдлинные записи режутся
   по предложениям (razdel).
3. ``chapter`` — целая глава (для «Фауста» — сцена) как чанк. Честный
   конкурент для BM25; для dense заведомо плох (обрезка на 512 токенах
   e5) — это часть сравнения.

Целевой размер окна по умолчанию — 180 слов: русское слово в токенизаторе
e5 ≈ 2–2.5 токена, лимит модели 512, значит безопасный чанк ≤ ~200 слов.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field

from razdel import sentenize

BOOK_TITLES = {
    "prestuplenie_i_nakazanie": "Преступление и наказание",
    "idiot": "Идиот",
    "besy": "Бесы",
    "faust_holodkovsky": "Фауст",
}

TARGET_WORDS = 180
# Жёсткий потолок одной единицы: длиннее — режем по предложениям.
MAX_UNIT_WORDS = 200


@dataclass
class Chunk:
    book: str
    text: str
    strategy: str
    para_ids: list[int] = field(default_factory=list)
    part: str | None = None
    chapter: str | None = None
    chapter_title: str | None = None
    section: str | None = None
    scene: str | None = None
    speakers: list[str] = field(default_factory=list)

    @property
    def citation(self) -> str:
        """Человекочитаемый адрес для обязательного цитирования в ответе."""
        title = BOOK_TITLES.get(self.book, self.book)
        bits = [title]
        if self.scene:
            if self.part:
                bits.append(f"часть {self.part}")
            bits.append(f"сцена «{self.scene.capitalize()}»")
        else:
            if self.part:
                bits.append(f"часть {self.part}")
            if self.chapter:
                name = f"глава {self.chapter}"
                if self.chapter_title:
                    name += f" «{self.chapter_title}»"
                bits.append(name)
            if self.section:
                bits.append(f"раздел {self.section}")
        return ", ".join(bits)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Chunk:
        return cls(**d)


def _n_words(s: str) -> int:
    return len(s.split())


def _split_long(text: str, max_words: int) -> list[str]:
    """Режет сверхдлинный текст по предложениям на куски <= max_words."""
    if _n_words(text) <= max_words:
        return [text]
    pieces: list[str] = []
    cur: list[str] = []
    cur_words = 0
    for sent in sentenize(text):
        w = _n_words(sent.text)
        if cur and cur_words + w > max_words:
            pieces.append(" ".join(cur))
            cur, cur_words = [], 0
        cur.append(sent.text)
        cur_words += w
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def _group_key(r: dict) -> tuple:
    """Граница, которую чанк не пересекает: глава романа или сцена драмы."""
    return (r["book"], r["part"], r["chapter"], r.get("scene"))


def _grouped(records: Iterable[dict]) -> Iterator[list[dict]]:
    group: list[dict] = []
    key = None
    for r in records:
        k = _group_key(r)
        if group and k != key:
            yield group
            group = []
        group.append(r)
        key = k
    if group:
        yield group


def _unit_text(r: dict) -> str:
    """Единица упаковки; реплике драмы предшествует имя говорящего."""
    if r.get("speaker"):
        return f"{r['speaker']}: {r['text']}"
    return r["text"]


def _make_chunk(group: list[dict], units: list[tuple[int, str]], strategy: str) -> Chunk:
    by_id = {r["para_id"]: r for r in group}
    # адрес чанка — по первой записи окна (раздел внутри главы может меняться)
    first = by_id[units[0][0]]
    speakers = sorted(
        {by_id[pid]["speaker"] for pid, _ in units if by_id.get(pid, {}).get("speaker")}
    )
    return Chunk(
        book=first["book"],
        text="\n".join(t for _, t in units),
        strategy=strategy,
        para_ids=sorted({pid for pid, _ in units}),
        part=first["part"],
        chapter=first["chapter"],
        chapter_title=first.get("chapter_title"),
        section=first.get("section"),
        scene=first.get("scene"),
        speakers=speakers,
    )


def chunk_paragraph(records: Iterable[dict]) -> list[Chunk]:
    """Базлайн: одна запись = один чанк (сверхдлинные всё же режем)."""
    chunks: list[Chunk] = []
    for group in _grouped(records):
        for r in group:
            for piece in _split_long(_unit_text(r), MAX_UNIT_WORDS):
                chunks.append(_make_chunk([r], [(r["para_id"], piece)], "paragraph"))
    return chunks


def chunk_window(records: Iterable[dict], target_words: int = TARGET_WORDS) -> list[Chunk]:
    """Окна с перекрытием в одну единицу, в пределах главы/сцены."""
    chunks: list[Chunk] = []
    for group in _grouped(records):
        units: list[tuple[int, str]] = []
        for r in group:
            for piece in _split_long(_unit_text(r), MAX_UNIT_WORDS):
                units.append((r["para_id"], piece))
        cur: list[tuple[int, str]] = []
        cur_words = 0
        for unit in units:
            w = _n_words(unit[1])
            if cur and cur_words + w > target_words:
                chunks.append(_make_chunk(group, cur, "window"))
                last, last_w = cur[-1], _n_words(cur[-1][1])
                # перекрытие: последняя единица переходит в следующее окно,
                # но только короткая — иначе окна растут без предела
                if last_w <= target_words // 2:
                    cur, cur_words = [last], last_w
                else:
                    cur, cur_words = [], 0
            cur.append(unit)
            cur_words += w
        if cur:
            chunks.append(_make_chunk(group, cur, "window"))
    return chunks


def chunk_chapter(records: Iterable[dict]) -> list[Chunk]:
    """Глава романа / сцена драмы целиком."""
    chunks: list[Chunk] = []
    key = None
    group_all: list[dict] = []

    def flush() -> None:
        if group_all:
            units = [(r["para_id"], _unit_text(r)) for r in group_all]
            chunks.append(_make_chunk(group_all, units, "chapter"))

    for r in records:
        # у романов раздел (римская цифра в «Бесах») не граница главы
        k = (r["book"], r["part"], r["chapter"], r.get("scene"))
        if group_all and k != key:
            flush()
            group_all = []
        group_all.append(r)
        key = k
    flush()
    return chunks


STRATEGIES = {
    "paragraph": chunk_paragraph,
    "window": chunk_window,
    "chapter": chunk_chapter,
}


def chunk_records(records: Iterable[dict], strategy: str, **kwargs) -> list[Chunk]:
    try:
        fn = STRATEGIES[strategy]
    except KeyError as e:
        raise ValueError(f"Неизвестная стратегия: {strategy!r}; есть {sorted(STRATEGIES)}") from e
    return fn(records, **kwargs)
