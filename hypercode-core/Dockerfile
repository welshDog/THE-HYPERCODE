
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
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
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libatomic1 \
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
RUN prisma generate

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
