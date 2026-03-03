# Multi-stage build for AI News Summarizer
# Stage 1: Builder stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/

# Copy startup script
COPY start.sh ./start.sh
RUN chmod +x start.sh

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose port (configurable via environment variable)
EXPOSE 8080


# Health check - use PORT env var or default to 8080
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8080'); urllib.request.urlopen(f'http://localhost:{port}/api/health').read()"

# Run the application with startup script
CMD ["bash", "./start.sh"]
