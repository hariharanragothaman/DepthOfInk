FROM python:3.13-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target /deps -r requirements.txt

FROM python:3.13-slim

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app
COPY --from=builder /deps /usr/local/lib/python3.13/site-packages
COPY app/ app/

ENV DATA_DIR=/app/data \
    UPLOADS_DIR=/app/data/uploads \
    CHROMA_DIR=/app/data/chroma \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/data/uploads /app/data/chroma /app/data/books && \
    chown -R appuser:appuser /app/data

EXPOSE 8000

USER appuser

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
