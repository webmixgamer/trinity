FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic

COPY ../../src/audit-logger/audit_logger.py /app/

# Default port (can be overridden by PORT env var)
EXPOSE 8001

CMD ["python", "audit_logger.py"]

