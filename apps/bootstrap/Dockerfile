FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/bootstrap/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bootstrap src and common code
COPY apps/bootstrap/src/ /app/src/
COPY common/ /app/src/common/

ENV PYTHONPATH="${PYTHONPATH}:/app/src:/app/src/common"

WORKDIR /app/src

CMD ["python", "main.py"]
