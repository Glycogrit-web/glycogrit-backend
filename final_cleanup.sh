#!/bin/bash
#
# Final Cleanup Script - Phase 1
# Safe removal of unused legacy code
#

set -e
cd "$(dirname "$0")"

echo "🧹 Starting Final Cleanup - Phase 1"
echo "========================================"
echo ""

# Step 1: Move validators to core
echo "📦 Step 1: Moving validators.py to core..."
if [ -f "app/schemas/validators.py" ]; then
    cp app/schemas/validators.py app/core/validators.py
    echo "   ✅ Copied validators.py to app/core/"
else
    echo "   ⚠️  validators.py not found, skipping"
fi

# Step 2: Move tier schema to core (if needed by events module)
echo ""
echo "📦 Step 2: Moving tier.py to core..."
if [ -f "app/schemas/tier.py" ]; then
    cp app/schemas/tier.py app/core/tier_schemas.py
    echo "   ✅ Copied tier.py to app/core/tier_schemas.py"
else
    echo "   ⚠️  tier.py not found, skipping"
fi

# Step 3: Move base repository to core
echo ""
echo "📦 Step 3: Moving base repository to core..."
if [ -f "app/repositories/base.py" ]; then
    mkdir -p app/core/repository
    cp app/repositories/base.py app/core/repository/base.py
    echo "   ✅ Copied base.py to app/core/repository/"
else
    echo "   ⚠️  base.py not found, skipping"
fi

echo ""
echo "✅ Phase 1 Complete - Files copied to core/"
echo ""
echo "📋 Next Steps (Manual):"
echo "   1. Update imports in these files:"
echo "      - app/core/dependencies.py"
echo "      - app/modules/payments/repositories/payment_repository.py"
echo "      - app/modules/users/repositories/user_repository.py"
echo "      - app/modules/activities/repositories/activity_repository.py"
echo "      - app/modules/activities/repositories/progress_repository.py"
echo "      - app/modules/users/schemas/auth.py"
echo "      - app/modules/events/schemas/event.py"
echo ""
echo "   2. Change imports from:"
echo "      from app.repositories.base import X"
echo "      to:"
echo "      from app.core.repository.base import X"
echo ""
echo "   3. Change imports from:"
echo "      from app.schemas.validators import X"
echo "      to:"
echo "      from app.core.validators import X"
echo ""
echo "   4. Run tests to verify: pytest tests/"
echo ""
echo "   5. If all tests pass, remove old directories:"
echo "      rm -rf app/repositories/"
echo "      rm -rf app/schemas/"
echo ""
echo "⚠️  Do NOT remove directories yet - update imports first!"
