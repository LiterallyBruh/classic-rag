"""Сравнение с baseline: чистый LLM (без RAG) против ClassicLiteratureRAG.

Продуктовая гипотеза проекта: универсальные LLM галлюцинируют цитатами
и адресами по классике, а RAG с обязательным цитированием — нет.
Скрипт проверяет это количественно на подвыборке eval-набора.

Метрики (все автоматические, проверяемые):
- quote_verbatim: все закавыченные фрагменты (>=4 слов) из ответа
  дословно находятся в тексте книги (нормализация: регистр, ё, пунктуация).
  Ловит главный вид галлюцинаций — выдуманные «цитаты».
- gold_hit: в ответе есть золотая подстрока вопроса (gold_match) —
  модель опирается на правильное место текста.
- addr_hit: названные часть/глава совпадают с золотыми (кроме «Фауста»,
  где адрес — имя сцены; там метрика не считается).
- refused: система честно отказалась (только ClassicLiteratureRAG: baseline
  отказываться не обязан, но и не наказывается за отказ).

Запуск: python eval/compare_baseline.py [--n-factual 2] [--out eval/baseline_comparison.md]
Ключи LLM — из .env (см. .env.example).
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from dotenv import load_dotenv

from classic_rag.chunking import BOOK_TITLES
from classic_rag.generate import REFUSAL
from classic_rag.llm import default_model, make_client
from classic_rag.pipeline import RagPipeline

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "eval" / "questions.jsonl"
PROCESSED = ROOT / "data" / "processed"

BASELINE_PROMPT = """Ты — ассистент по классической литературе.
Ответь на вопрос по произведению «{title}» ({author}).
Подкрепи ответ короткой цитатой из текста и укажи часть и главу."""

AUTHORS = {
    "prestuplenie_i_nakazanie": "Ф. М. Достоевский",
    "idiot": "Ф. М. Достоевский",
    "besy": "Ф. М. Достоевский",
    "faust_holodkovsky": "И. В. Гёте, пер. Н. Холодковского",
}

_ORDINALS = {
    "перв": 1, "втор": 2, "трет": 3, "четверт": 4, "пят": 5,
    "шест": 6, "седьм": 7, "восьм": 8, "девят": 9, "десят": 10,
}


def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    return re.sub(r"[^а-яa-z0-9]+", " ", text).strip()


_morph = None


def lemmas(text: str) -> set[str]:
    """Множество лемм: «погиб»/«погибает» и «Сони»/«Соне» должны совпадать."""
    global _morph
    if _morph is None:
        import pymorphy3  # тяжёлый импорт — лениво

        _morph = pymorphy3.MorphAnalyzer()
    return {
        _morph.parse(w)[0].normal_form
        for w in normalize(text).split()
        if len(w) > 2  # предлоги/союзы не должны надувать пересечение
    }


_ADDR_SPAN = re.compile(r"часть\s+\d|глава\s+\d", re.IGNORECASE)


def quoted_spans(answer: str, min_words: int = 4) -> list[str]:
    """Закавыченные фрагменты-цитаты. Кавычки вокруг адресов не считаются:
    названия сцен («сцена „Ночь"») и ссылки («Идиот», часть 4, глава 11) —
    это цитирование адреса, а не текста."""
    out = []
    for m in re.finditer(r"«([^»]+)»|\"([^\"]+)\"|„([^“]+)“", answer):
        span = next(s for s in m.groups() if s)
        before = answer[max(0, m.start() - 12):m.start()].lower()
        if any(w in before for w in ("сцен", "часть", "глав")):
            continue
        if _ADDR_SPAN.search(span) or normalize(span) in map(normalize, BOOK_TITLES.values()):
            continue
        if len(span.split()) >= min_words:
            out.append(span)
    return out


def extract_addr(answer: str, kind: str) -> set[int]:
    """Номера частей ('част') или глав ('глав'), названные в ответе."""
    out: set[int] = set()
    for m in re.finditer(kind + r"\w*\s+(\d+|[а-яё]+)", answer.lower()):
        token = m.group(1)
        if token.isdigit():
            out.add(int(token))
        else:
            for stem, num in _ORDINALS.items():
                if token.startswith(stem):
                    out.add(num)
    return out


def score(answer: str, q: dict, book_text: str) -> dict:
    refused = REFUSAL.lower().rstrip(".») ") in answer.lower()
    spans = quoted_spans(answer)
    verbatim = all(normalize(s) in book_text for s in spans) if spans else None
    censored = "языковые модели не обладают" in answer.lower()
    # верность ответа по сути: >=половины лемм эталонного ответа присутствуют
    # (леммы, а не слова: «Соне»/«Соня» — совпадение);
    # отказ любой природы верным ответом не считается
    ref = lemmas(q["reference_answer"])
    gold = (
        not (refused or censored)
        and len(ref & lemmas(answer)) >= max(1, len(ref) // 2)
    )
    addr = None
    if q["book"] != "faust_holodkovsky" and q.get("chapter") and not refused:
        stated = extract_addr(answer, "глав")
        if stated and q["chapter"].isdigit():
            addr = int(q["chapter"]) in stated
    return {
        "refused": refused,
        "censored": censored,
        "has_quote": bool(spans),
        "quote_verbatim": verbatim,
        "gold_hit": gold,
        "addr_hit": addr,
    }


def sample_questions(n_factual: int, seed: int = 42) -> list[dict]:
    qs = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines()]
    picked = [q for q in qs if q["type"] == "quote"]
    rng = random.Random(seed)
    for book in BOOK_TITLES:
        factual = [q for q in qs if q["book"] == book and q["type"] == "factual"]
        picked += rng.sample(factual, min(n_factual, len(factual)))
    return picked


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-factual", type=int, default=2, help="factual-вопросов на книгу")
    ap.add_argument("--out", default="eval/baseline_comparison.md")
    ap.add_argument("--raw", default="eval/baseline_raw.json", help="сырые ответы для аудита")
    ap.add_argument("--rescore", action="store_true",
                    help="пересчитать метрики по сохранённым ответам, без вызовов LLM")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    book_texts = {
        book: normalize(
            " ".join(
                json.loads(line)["text"]
                for line in (PROCESSED / f"{book}.jsonl").read_text(encoding="utf-8").splitlines()
            )
        )
        for book in BOOK_TITLES
    }

    questions = sample_questions(args.n_factual)
    if args.rescore:
        raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
        answers = {r["question"]: r for r in raw}
        rows = [
            (q, score(answers[q["question"]]["baseline"], q, book_texts[q["book"]]),
             score(answers[q["question"]]["rag"], q, book_texts[q["book"]]))
            for q in questions
        ]
        write_report(rows, Path(args.out), default_model())
        return

    client = make_client()
    model = default_model()
    pipeline = RagPipeline.from_index()
    rows, raw = [], []
    for i, q in enumerate(questions, 1):
        title = BOOK_TITLES[q["book"]]
        print(f"[{i}/{len(questions)}] {q['question'][:60]}", flush=True)

        base = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {"role": "system",
                 "content": BASELINE_PROMPT.format(title=title, author=AUTHORS[q["book"]])},
                {"role": "user", "content": q["question"]},
            ],
        ).choices[0].message.content or ""
        rag = pipeline.ask(q["question"], book=q["book"]).answer

        rows.append((q, score(base, q, book_texts[q["book"]]),
                     score(rag, q, book_texts[q["book"]])))
        raw.append({"question": q["question"], "book": q["book"], "type": q["type"],
                    "baseline": base, "rag": rag})

    Path(args.raw).write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(rows, Path(args.out), model)


def _pct(hits: list[bool | None]) -> str:
    known = [h for h in hits if h is not None]
    return f"{sum(known)}/{len(known)}" if known else "—"


def _fabricated(scores: list[dict]) -> str:
    """Ответы, где есть закавыченная «цитата», не найденная в тексте дословно.
    Знаменатель — все вопросы: метрика сопоставима между системами."""
    bad = sum(s["has_quote"] and s["quote_verbatim"] is False for s in scores)
    return f"{bad}/{len(scores)}"


def write_report(rows: list, out: Path, model: str) -> None:
    base_scores = [b for _, b, _ in rows]
    rag_scores = [r for _, _, r in rows]

    def agg(scores: list[dict], key: str) -> str:
        return _pct([s[key] for s in scores])

    lines = [
        "# Baseline (LLM без RAG) vs ClassicLiteratureRAG",
        "",
        f"Модель в обеих системах: {model}. Вопросы — подвыборка eval-набора",
        "(все quote + по 2 factual на книгу), метрики автоматические,",
        "методика — в докстринге eval/compare_baseline.py, сырые ответы —",
        "в eval/baseline_raw.json.",
        "",
        "Ключевой результат: по существу обе системы отвечают сопоставимо,",
        "но у LLM без RAG **все** закавыченные «цитаты» выдуманы (0 дословных),",
        "а номер главы верен лишь эпизодически — то есть проверить его ответ",
        "школьник не может. ClassicLiteratureRAG цитирует дословно, адресует верно,",
        "а когда retrieval не находит опоры — честно отказывается вместо",
        "правдоподобного вранья. Показательный улов метрики: даже «почти",
        "верная» цитата RAG однажды сжала авторское «главнейший и, может",
        "быть, единственный закон бытия» до «главнейший закон бытия» —",
        "автоматическая сверка ловит и это.",
        "",
        "| Метрика | LLM без RAG | ClassicLiteratureRAG |",
        "|---|---|---|",
        f"| Цитаты дословно из текста* | {agg(base_scores, 'quote_verbatim')} "
        f"| {agg(rag_scores, 'quote_verbatim')} |",
        f"| Ответы с выдуманной цитатой | {_fabricated(base_scores)} "
        f"| {_fabricated(rag_scores)} |",
        f"| Ответ верен по сути | {agg(base_scores, 'gold_hit')} "
        f"| {agg(rag_scores, 'gold_hit')} |",
        f"| — среди данных ответов (без отказов) | "
        f"{_pct([s['gold_hit'] for s in base_scores if not (s['refused'] or s['censored'])])} | "
        f"{_pct([s['gold_hit'] for s in rag_scores if not (s['refused'] or s['censored'])])} |",
        f"| Верный номер главы | {agg(base_scores, 'addr_hit')} "
        f"| {agg(rag_scores, 'addr_hit')} |",
        f"| Честные отказы («в тексте ответа нет») | — "
        f"| {sum(s['refused'] for s in rag_scores)}/{len(rag_scores)} |",
        f"| Цензурные отказы GigaChat | {sum(s['censored'] for s in base_scores)}"
        f"/{len(base_scores)} | {sum(s['censored'] for s in rag_scores)}/{len(rag_scores)} |",
        "",
        "\\* знаменатель — ответы, в которых есть закавыченные цитаты (от 4 слов):",
        "baseline «цитирует» почти всегда, ClassicLiteratureRAG — только когда",
        "во фрагментах есть опора; поэтому строкой ниже та же разница дана",
        "с общим знаменателем — доля ответов с выдуманной цитатой.",
        "",
        "## По вопросам",
        "",
        "| Вопрос | Тип | Цитата дословна (base/RAG) | По сути (base/RAG) |",
        "|---|---|---|---|",
    ]

    def mark(v: bool | None) -> str:
        return "—" if v is None else ("✅" if v else "❌")

    for q, b, r in rows:
        lines.append(
            f"| {q['question'][:70]} | {q['type']} "
            f"| {mark(b['quote_verbatim'])} / {mark(r['quote_verbatim'])} "
            f"| {mark(b['gold_hit'])} / {mark(r['gold_hit'])} |"
        )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Отчёт: {out}")


if __name__ == "__main__":
    main()
