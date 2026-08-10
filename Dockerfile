# Multi-stage build for NeoShare-Local-Cloud
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY server.py ./
COPY index.html ./
COPY styles.css ./
COPY script.js ./

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Create non-root user
RUN groupadd -r neoshare && useradd -r -g neoshare neoshare

# Copy application from builder
COPY --from=builder /app /app

# Set ownership
RUN chown -R neoshare:neoshare /app

# Expose default port
EXPOSE 8000

# Run as non-root user
USER neoshare

# Environment variables (can be overridden at runtime)
ENV PORT=8000
ENV BASE_DIR=/app
ENV MAX_UPLOAD_SIZE=2147483648

ENTRYPOINT ["python3", "server.py"]