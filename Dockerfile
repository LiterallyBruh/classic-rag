FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir -e .
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0"]
