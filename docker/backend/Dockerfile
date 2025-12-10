FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck, git for GitHub cloning
RUN apt-get update && apt-get install -y --no-install-recommends curl git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    python-multipart==0.0.6 \
    websockets==12.0 \
    redis==5.0.1 \
    httpx==0.25.2 \
    pyyaml==6.0.1 \
    "urllib3<2" \
    "requests<2.32" \
    docker==7.0.0 \
    requests-unixsocket==0.3.0 \
    aiofiles==23.2.1 \
    apscheduler==3.10.4 \
    croniter==2.0.1 \
    pytz==2024.1

# Copy all backend source files
COPY ../../src/backend/main.py /app/
COPY ../../src/backend/config.py /app/
COPY ../../src/backend/models.py /app/
COPY ../../src/backend/db_models.py /app/
COPY ../../src/backend/dependencies.py /app/
COPY ../../src/backend/credentials.py /app/
COPY ../../src/backend/database.py /app/

# Copy module directories
COPY ../../src/backend/routers /app/routers/
COPY ../../src/backend/services /app/services/
COPY ../../src/backend/utils /app/utils/
COPY ../../src/backend/db /app/db/

# Ensure all files are readable
RUN chmod -R 644 /app/*.py && \
    chmod -R 755 /app/routers /app/services /app/utils /app/db && \
    find /app/routers /app/services /app/utils /app/db -name "*.py" -exec chmod 644 {} \;

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

