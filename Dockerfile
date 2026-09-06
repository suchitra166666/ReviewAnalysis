FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY rap ./rap
COPY config ./config
COPY alembic.ini ./
COPY docs ./docs

RUN uv pip install --system -e .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "rap api --host 0.0.0.0 --port ${PORT:-8000}"]
