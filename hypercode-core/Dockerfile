# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt \
    && pip install --user --no-cache-dir prisma

ENV PATH=/root/.local/bin:$PATH

COPY prisma ./prisma
RUN prisma generate

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libatomic1 \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m appuser

COPY --from=builder /root/.local /home/appuser/.local

COPY . .

RUN chown -R appuser:appuser /app /home/appuser

# Run as root in runtime to avoid prisma cache permission issues in demo
# For production, prefer running as non-root and set prisma cache dir appropriately
USER root

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/home/appuser/.local/lib/python3.11/site-packages

# Prisma client already generated in builder stage

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=20s \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS}
