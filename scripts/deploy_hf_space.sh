#!/usr/bin/env bash
# Деплой демо на HF Spaces (Docker Space).
#
# Space — отдельный git-репозиторий; этот скрипт собирает его содержимое
# из основного репо (единый источник правды) и пушит. Отличия от основного
# репо, оба осознанные:
#   1) в Space кладём готовый индекс (data/index/window) — иначе контейнер
#      на бесплатном CPU пересобирал бы эмбеддинги ~30+ минут при каждом
#      рестарте; embeddings.npy > 10 МБ, поэтому git-lfs;
#   2) в Dockerfile добавляется COPY data ./data (в основном репо data/
#      вне контекста сборки и живёт в docker-volume).
#
# Использование:
#   HF_TOKEN=hf_... scripts/deploy_hf_space.sh [git-url-спейса]
# Секрет GIGACHAT_AUTH_KEY задаётся один раз в Settings спейса (или через
# API, см. README).

set -euo pipefail

SPACE_URL="${1:-https://huggingface.co/spaces/ArtemResearch/ClassicLiteratureRAG}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

[[ -n "${HF_TOKEN:-}" ]] || { echo "HF_TOKEN не задан" >&2; exit 1; }
[[ -f "$ROOT/data/index/window/embeddings.npy" ]] \
    || { echo "Индекс не собран: python scripts/bootstrap.py" >&2; exit 1; }

AUTH_URL="$(printf '%s' "$SPACE_URL" | sed "s|^https://|https://user:${HF_TOKEN}@|")"
git clone --depth 1 "$AUTH_URL" "$WORK/space"

cd "$WORK/space"
git lfs install --local

# --- содержимое из основного репо ---------------------------------------
rsync -a --delete --exclude ".git" --exclude "__pycache__" --exclude "*.egg-info" \
    "$ROOT/src" "$ROOT/app" "$ROOT/scripts" "$ROOT/configs" ./
cp "$ROOT/pyproject.toml" ./
mkdir -p data/index
rsync -a --delete "$ROOT/data/index/window" data/index/

# --- отличия Space (см. шапку) -------------------------------------------
sed 's|^COPY configs ./configs$|COPY configs ./configs\nCOPY data ./data|' \
    "$ROOT/Dockerfile" > Dockerfile
grep -v '^data$' "$ROOT/.dockerignore" > .dockerignore

cat > .gitattributes <<'EOF'
*.npy filter=lfs diff=lfs merge=lfs -text
EOF

cat > README.md <<'EOF'
---
title: ClassicRAG
emoji: 📚
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 8501
pinned: false
---

# 📚 ClassicRAG

Вопросно-ответная система по русской и мировой классике: отвечает **только
по тексту первоисточника**, с цитатами и указанием части/главы.

Основной репозиторий с кодом, тестами и метриками — на GitHub
(этот Space — только демо). Генерация — GigaChat; без секрета
`GIGACHAT_AUTH_KEY` демо работает в режиме «только найденные фрагменты».
EOF

git add -A
if git diff --cached --quiet; then
    echo "Изменений нет — пушить нечего"
    exit 0
fi
git -c user.name="deploy" -c user.email="deploy@local" \
    commit -m "Deploy from main repo $(git -C "$ROOT" rev-parse --short HEAD)"
git push origin main
echo "Готово: ${SPACE_URL}"
