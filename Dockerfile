FROM python:3.10-slim

WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements
COPY requirements.txt .

# Install with minimal cache
RUN pip install --no-cache-dir --no-deps -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p logs data config

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Start bot
CMD ["python", "-m", "mie.main", "scheduler"]
