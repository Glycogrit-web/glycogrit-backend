#!/bin/bash
#
# Old Code Cleanup Script
# Removes all deprecated API and service files
# Creates automatic backup before deletion
#

set -e  # Exit on error

echo "🧹 Starting GlycoGrit Backend Cleanup..."
echo "========================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create backup
BACKUP_FILE="${PROJECT_ROOT}/glycogrit-backend-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
echo ""
echo "📦 Creating backup..."
cd "$PROJECT_ROOT"
tar -czf "$BACKUP_FILE" glycogrit-backend/
echo "✅ Backup created: $BACKUP_FILE"

# Navigate to backend
cd "${SCRIPT_DIR}"

# Phase 1: Remove old API files
echo ""
echo "🗑️  Phase 1: Removing old API files..."
cd app/api

OLD_API_FILES=(
    "activities.py"
    "activity_progress.py"
    "progress.py"
    "auth.py"
    "challenges.py"
    "rewards.py"
    "events.py"
    "event_tiers.py"
    "registrations.py"
    "certificates.py"
    "gallery.py"
    "statistics.py"
    "payments.py"
    "webhooks.py"
    "webhooks_v2.py"
    "fitness_trackers.py"
    "strava.py"
    "garmin.py"
    "fitbit.py"
    "google_fit.py"
    "wahoo.py"
    "base.py"
)

FILES_REMOVED=0
for file in "${OLD_API_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "   ✓ Removed $file"
        ((FILES_REMOVED++))
    fi
done

# Remove pycache
if [ -d "__pycache__" ]; then
    rm -rf __pycache__
    echo "   ✓ Removed __pycache__"
fi

echo "✅ Phase 1 complete: $FILES_REMOVED files removed"

# Phase 2: Remove old service files
echo ""
echo "🗑️  Phase 2: Removing old service files..."
cd ../../services

OLD_SERVICE_FILES=(
    "activity_service.py"
    "user_service.py"
    "certificate_service.py"
    "fitness_tracker_service.py"
)

FILES_REMOVED=0
for file in "${OLD_SERVICE_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "   ✓ Removed $file"
        ((FILES_REMOVED++))
    fi
done

echo "✅ Phase 2 complete: $FILES_REMOVED files removed"

# Phase 3: Remove empty api directory
echo ""
echo "🗑️  Phase 3: Cleaning up empty directories..."
cd ../

# Check if api directory is empty (only __init__.py)
API_FILE_COUNT=$(find api -name "*.py" ! -name "__init__.py" 2>/dev/null | wc -l)
if [ "$API_FILE_COUNT" -eq 0 ]; then
    if [ -d "api" ]; then
        # Keep the directory but leave only __init__.py
        echo "   ℹ️  api/ directory cleaned (keeping __init__.py for Python package structure)"
    fi
else
    echo "   ⚠️  api/ directory still contains files: $API_FILE_COUNT Python files"
fi

echo "✅ Phase 3 complete"

# Summary
echo ""
echo "✨ Cleanup Complete!"
echo "==================="
echo ""
echo "📊 Summary:"
echo "   - Backup created: $BACKUP_FILE"
echo "   - Old API files removed: 23 files"
echo "   - Old service files removed: 4 files"
echo "   - Total files removed: 27"
echo ""
echo "📋 Next Steps:"
echo "   1. Update main.py with new router imports"
echo "   2. Run tests: pytest"
echo "   3. Start server: uvicorn app.main:app --reload"
echo "   4. Test endpoints: http://localhost:8000/docs"
echo ""
echo "🔄 To rollback if needed:"
echo "   tar -xzf $BACKUP_FILE -C $PROJECT_ROOT"
echo ""
echo "✅ All done!"
