FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

# Metadata
LABEL maintainer="viermart@gmail.com"
LABEL version="2.1-debug-system"

# Run the application
CMD ["python", "main.py"]
