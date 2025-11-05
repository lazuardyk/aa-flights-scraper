# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for curl-cffi
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scraper script
COPY scrape.py .

# Create output directory
RUN mkdir -p /output

# Set environment variable for output
ENV OUTPUT_DIR=/output

# Default command (can be overridden)
ENTRYPOINT ["python", "scrape.py"]
CMD ["--help"]
