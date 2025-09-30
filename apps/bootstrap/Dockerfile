FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bootstrap src and common code
COPY ./src/ ./src/
COPY ../../common/ ./common/

ENV PYTHONPATH="${PYTHONPATH}:/app/src:/app/common"

WORKDIR /app/src

CMD ["python", "main.py"]
