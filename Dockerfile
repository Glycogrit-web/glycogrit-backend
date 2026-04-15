FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create startup script with comprehensive logging
RUN echo '#!/bin/bash\n\
set -e\n\
echo "================================================"\n\
echo "🚀 Starting GlycoGrit Backend Deployment"\n\
echo "================================================"\n\
echo ""\n\
echo "📊 Environment Information:"\n\
echo "  - PORT: ${PORT:-8000}"\n\
echo "  - ENVIRONMENT: ${ENVIRONMENT:-development}"\n\
echo "  - RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"\n\
echo "  - DATABASE_URL: ${DATABASE_URL:0:50}..." \n\
echo "  - ALLOWED_ORIGINS: ${ALLOWED_ORIGINS:-not set}"\n\
echo ""\n\
echo "📦 Python Version:"\n\
python --version\n\
echo ""\n\
echo "📦 Installed Packages:"\n\
pip list | grep -E "(fastapi|uvicorn|sqlalchemy|alembic|pydantic)" || echo "Core packages check failed"\n\
echo ""\n\
echo "🗄️  Database Connection Test:"\n\
if [ ! -z "$DATABASE_URL" ]; then\n\
  echo "  ✅ DATABASE_URL is set"\n\
  echo "  Testing database connectivity..."\n\
  python -c "from sqlalchemy import create_engine; import sys; \\\n\
try: \\\n\
  engine = create_engine(\"$DATABASE_URL\"); \\\n\
  conn = engine.connect(); \\\n\
  print(\"  ✅ Database connection successful\"); \\\n\
  conn.close(); \\\n\
except Exception as e: \\\n\
  print(f\"  ❌ Database connection failed: {e}\"); \\\n\
  sys.exit(1)" || { echo "  ⚠️  Database test failed but continuing..."; }\n\
  echo ""\n\
  echo "🔄 Running Database Migrations:"\n\
  alembic upgrade head || { echo "  ⚠️  Migrations failed or skipped"; }\n\
else\n\
  echo "  ⚠️  DATABASE_URL not set, skipping database operations"\n\
fi\n\
echo ""\n\
echo "🌐 Starting Web Server:"\n\
echo "  - Binding to: 0.0.0.0:${PORT:-8000}"\n\
echo "  - Health check: http://localhost:${PORT:-8000}/health"\n\
echo "  - API docs: http://localhost:${PORT:-8000}/docs"\n\
echo ""\n\
echo "================================================"\n\
echo "✅ Startup complete, launching uvicorn..."\n\
echo "================================================"\n\
echo ""\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Run the startup script
CMD ["/app/start.sh"]
