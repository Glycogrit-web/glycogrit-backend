FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create simple startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting GlycoGrit Backend"\n\
echo "PORT: ${PORT:-8000}"\n\
echo "ENVIRONMENT: ${ENVIRONMENT:-development}"\n\
echo ""\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Run the startup script
CMD ["/app/start.sh"]
