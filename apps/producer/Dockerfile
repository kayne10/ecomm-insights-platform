# Use certified Python 3.13 slim image
FROM python:3.13-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (needed for confluent-kafka)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY apps/producer/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the producer src code
COPY apps/producer/src/ /app/src/

# Copy shared common code
COPY common/ /app/src/common/

# Add src to PYTHONPATH so imports work nicely
ENV PYTHONPATH="${PYTHONPATH}:/app/src:/app/src/common"

# Set default working directory to src
WORKDIR /app/src

# Default command: run main.py
CMD ["python", "main.py"]
