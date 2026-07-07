"""Сбор пользовательского фидбека из демо (критерий «продукт», D-013).

Каждая запись пишется локально в data/feedback/feedback.jsonl. Диск на
HF Space эфемерный (теряется при рестарте контейнера), поэтому при заданных
FEEDBACK_DATASET (приватный HF-датасет, например "user/classicrag-feedback")
и HF_TOKEN запись дублируется туда отдельным файлом — по файлу на отзыв,
чтобы не было гонок read-modify-write между сессиями.

Сбой выгрузки не должен ронять демо: он логируется, локальная запись
при этом уже сделана.
"""

from __future__ import annotations

import io
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_ROOT = Path("data/feedback")


def save_feedback(record: dict, root: Path = DEFAULT_ROOT) -> dict:
    """Дополняет запись меткой времени, пишет локально и (опц.) в HF-датасет."""
    record = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), **record}
    root.mkdir(parents=True, exist_ok=True)
    with (root / "feedback.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    dataset = os.getenv("FEEDBACK_DATASET")
    token = os.getenv("HF_TOKEN")
    if dataset and token:
        try:
            from huggingface_hub import HfApi  # ленивый импорт

            payload = json.dumps(record, ensure_ascii=False, indent=1).encode()
            HfApi(token=token).upload_file(
                path_or_fileobj=io.BytesIO(payload),
                path_in_repo=f"feedback/{record['ts']}-{uuid.uuid4().hex[:8]}.json",
                repo_id=dataset,
                repo_type="dataset",
            )
        except Exception:  # noqa: BLE001 — фидбек не должен ронять демо
            log.warning("не удалось выгрузить фидбек в %s", dataset, exc_info=True)
    return record
