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

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting GlycoGrit Backend..."\n\
echo "PORT: ${PORT:-8000}"\n\
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."\n\
\n\
# Run migrations if DATABASE_URL is set\n\
if [ ! -z "$DATABASE_URL" ]; then\n\
  echo "Running database migrations..."\n\
  alembic upgrade head || echo "Migrations skipped or failed"\n\
fi\n\
\n\
# Start the application\n\
echo "Starting uvicorn on port ${PORT:-8000}..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Run the startup script
CMD ["/app/start.sh"]
