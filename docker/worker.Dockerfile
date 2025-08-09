FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir poetry==1.6.1
COPY services/worker/pyproject.toml /app/
RUN poetry install --no-root

COPY services/worker /app
