FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runner

WORKDIR /app

RUN addgroup --system appuser && adduser --system --ingroup appuser --no-create-home appuser

COPY --from=builder --chown=appuser:appuser /install /usr/local

# Copia todo el directorio (incluyendo static/, templates/ y routers/)
COPY --chown=appuser:appuser . ./

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]