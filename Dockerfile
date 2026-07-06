# Демо ClassicRAG: Streamlit + гибридный retrieval.
# Корпус и индекс не запекаются в образ (data/ вне git и вне контекста
# сборки) — scripts/bootstrap.py строит их при первом старте, дальше
# они живут в volume (см. docker-compose.yml).

FROM python:3.11-slim

WORKDIR /app

# кэш HF-моделей — в volume, чтобы не скачивать e5/reranker при рестартах
ENV HF_HOME=/app/.cache/huggingface \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY src ./src
# CPU-колёса torch: дефолтный индекс на linux тянет гигабайты CUDA-библиотек,
# бесполезных для CPU-демо (HF Spaces basic — тоже CPU)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .

COPY app ./app
COPY scripts ./scripts
COPY configs ./configs

EXPOSE 8501
# HF Spaces передаёт свой порт в $PORT (для Docker Space — 7860)
CMD ["sh", "-c", "python scripts/bootstrap.py && streamlit run app/main.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
