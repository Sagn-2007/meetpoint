# Multi-stage Dockerfile for MeetPoint FastAPI Backend
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies for compiling any C-extensions if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libgeos-dev \
    libspatialindex-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final production runtime stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime spatial libraries and curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal36 \
    libgeos-c1t64 \
    libspatialindex-c8 \
    libspatialindex8 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root application user and group
RUN groupadd -g 10001 meetpoint && \
    useradd -u 10001 -g meetpoint -s /bin/bash -m meetpoint

# Copy backend application source, alembic migrations, and alembic.ini
COPY backend/app /app/app
COPY backend/alembic /app/alembic
COPY backend/alembic.ini /app/alembic.ini

# Ensure cache directory exists and has appropriate permissions
RUN mkdir -p /app/cache/osm_graphs && \
    chown -R meetpoint:meetpoint /app

USER meetpoint

EXPOSE 8000

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
