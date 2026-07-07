"""Тесты локальной записи фидбека (выгрузка в HF-датасет не мокается —
без FEEDBACK_DATASET/HF_TOKEN она просто не выполняется)."""

import json
from pathlib import Path

from classic_rag.feedback import save_feedback


def test_appends_jsonl_with_timestamp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FEEDBACK_DATASET", raising=False)
    save_feedback({"query": "q1", "rating": "up", "comment": ""}, root=tmp_path)
    save_feedback({"query": "q2", "rating": "down", "comment": "мимо"}, root=tmp_path)

    lines = (tmp_path / "feedback.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    assert first["query"] == "q1" and first["ts"]
    assert second["rating"] == "down" and second["comment"] == "мимо"
