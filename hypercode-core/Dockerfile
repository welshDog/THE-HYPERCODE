
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install dependencies to a local folder that we can copy
RUN pip install --user --no-cache-dir -r requirements.txt
RUN pip install --user --no-cache-dir prisma

# Set PATH for builder
ENV PATH=/root/.local/bin:$PATH

# Copy schema for generation
COPY prisma ./prisma
# Generate client
RUN prisma generate

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

# Change ownership of application code
RUN chown -R appuser:appuser /app
RUN chown -R appuser:appuser /home/appuser

# Explicitly download/ensure prisma binary exists in user space
# We re-run generate in runtime to ensure binaries are in the right place for the user
# This is safer than copying root cache
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN prisma generate

EXPOSE 8000

# Production-ready uvicorn; configure workers via UVICORN_WORKERS env if needed
ENV UVICORN_WORKERS=1
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD curl -sf http://localhost:8000/health || exit 1
CMD uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS}
