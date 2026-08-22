FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Install Python package
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "ai_engineering_os.main:app", "--host", "0.0.0.0", "--port", "8000"]
