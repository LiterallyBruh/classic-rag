# Деплой демо

## Локально (без Docker)

```bash
python scripts/bootstrap.py        # корпус + индекс (однократно)
streamlit run app/main.py
```

Без `LLM_API_KEY` в `.env` демо работает в режиме «только фрагменты».

## Docker

```bash
docker compose up --build
# первый старт: bootstrap скачает корпус и построит индекс (~5–10 мин),
# артефакты лягут в ./data и volume hf-cache — рестарты быстрые
```

## Hugging Face Spaces (Docker Space)

1. Создать Space: тип **Docker**, оборудование CPU basic (16 ГБ диска хватает:
   модели ~3.5 ГБ + индекс ~25 МБ).
2. Запушить репозиторий в Space (`git remote add space ...; git push space main`).
3. В начало `README.md` Space добавить фронтматтер:

   ```yaml
   ---
   title: ClassicLiteratureRAG
   emoji: "📚"
   sdk: docker
   app_port: 7860
   ---
   ```

4. В Settings → Variables and secrets задать `LLM_BASE_URL`, `LLM_API_KEY`,
   `LLM_MODEL` (secrets). Без них Space поднимется в режиме «только фрагменты».
5. Порт пробрасывается автоматически: CMD в Dockerfile читает `$PORT`
   (у Docker Space это 7860).

Первая сборка Space долгая: bootstrap при старте контейнера скачивает
корпус с az.lib.ru и строит индекс. Данные живут в контейнере — при
пересборке Space пересоздаются (persistent storage не требуется, но
ускоряет рестарты).
