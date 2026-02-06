# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /wheels prisma

# Generate Prisma Client
# We install prisma temporarily in builder to generate the client
RUN pip install --no-cache-dir prisma
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

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libatomic1 \
    openssl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m appuser

# Install wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy generated Prisma client
COPY --from=builder /build/prisma ./prisma

COPY . .

# Grant appuser permissions to site-packages for prisma client generation
RUN chown -R appuser:appuser /app && \
    chown -R appuser:appuser /usr/local/lib/python3.11/site-packages

# Run as appuser for security
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

# Generate Prisma Client in runtime environment as appuser
# This ensures binaries are stored in a location accessible to the user (e.g., ~/.cache)
# and the client code in site-packages is updated correctly.
RUN prisma generate

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=20s \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
