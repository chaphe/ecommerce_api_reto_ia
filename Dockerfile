# syntax=docker/dockerfile:1
# Multi-stage: build de dependencias aislado del runtime (imagen final más pequeña).

# ---------------------------------------------------------------------------
# Stage 1 — builder: resuelve wheels/paquetes sin dejar caché de pip en runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime: código + site-packages, proceso no root, puerto 8000
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN addgroup --system appuser \
    && adduser --system --ingroup appuser --no-create-home appuser

COPY --from=builder --chown=appuser:appuser /install /usr/local
COPY --chown=appuser:appuser config.py database.py models.py schemas.py crud.py main.py ./
COPY --chown=appuser:appuser routers ./routers

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
