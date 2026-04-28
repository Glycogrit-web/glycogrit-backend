#!/bin/bash
# Script to run database migrations

echo "Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
    exit 0
else
    echo "❌ Migration failed"
    exit 1
fi
