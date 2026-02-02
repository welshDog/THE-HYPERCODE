
# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser

# Copy only necessary files from builder
COPY --from=builder /root/.local /home/appuser/.local

# Update PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
