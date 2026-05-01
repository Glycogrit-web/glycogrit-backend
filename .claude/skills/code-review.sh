#!/bin/bash

# Code Review Skill Implementation
# Reviews code for adherence to GlycoGrit standards

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get the target file or directory
TARGET="${1:-.}"

echo "🔍 GlycoGrit Code Review"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if target exists
if [ ! -e "$TARGET" ]; then
    echo -e "${RED}✗ Error: Target not found: $TARGET${NC}"
    exit 1
fi

# Initialize counters
CRITICAL=0
WARNING=0
INFO=0

# Function to report issue
report_issue() {
    local severity=$1
    local file=$2
    local line=$3
    local message=$4

    case $severity in
        "critical")
            echo -e "${RED}🔴 CRITICAL${NC} $file:$line"
            echo "   $message"
            ((CRITICAL++))
            ;;
        "warning")
            echo -e "${YELLOW}🟡 WARNING${NC} $file:$line"
            echo "   $message"
            ((WARNING++))
            ;;
        "info")
            echo -e "${BLUE}🔵 INFO${NC} $file:$line"
            echo "   $message"
            ((INFO++))
            ;;
    esac
    echo ""
}

# Find all TypeScript/JavaScript files
if [ -d "$TARGET" ]; then
    FILES=$(find "$TARGET" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) | grep -v node_modules | grep -v dist | grep -v build)
elif [ -f "$TARGET" ]; then
    FILES="$TARGET"
else
    echo -e "${RED}✗ Invalid target${NC}"
    exit 1
fi

# If no files found
if [ -z "$FILES" ]; then
    echo -e "${YELLOW}⚠ No TypeScript/JavaScript files found${NC}"
    exit 0
fi

echo "📁 Reviewing files..."
echo ""

# Review each file
for file in $FILES; do
    # Skip if file doesn't exist (edge case)
    [ ! -f "$file" ] && continue

    filename=$(basename "$file")

    # Check 1: File naming conventions
    if [[ "$file" == *"/components/"* ]]; then
        # Component files should be PascalCase
        if [[ ! "$filename" =~ ^[A-Z][a-zA-Z0-9]*\.(tsx|jsx)$ ]]; then
            report_issue "warning" "$file" "1" "Component file should be PascalCase (e.g., ChallengeCard.tsx)"
        fi
    fi

    if [[ "$file" == *"/hooks/"* ]]; then
        # Hook files should be camelCase starting with 'use'
        if [[ ! "$filename" =~ ^use[A-Z][a-zA-Z0-9]*\.(ts|tsx)$ ]]; then
            report_issue "warning" "$file" "1" "Hook file should be camelCase starting with 'use' (e.g., useChallenges.ts)"
        fi
    fi

    # Check 2: TypeScript 'any' usage
    if grep -n ":\s*any" "$file" > /dev/null 2>&1; then
        line=$(grep -n ":\s*any" "$file" | head -1 | cut -d: -f1)
        report_issue "critical" "$file" "$line" "Avoid using 'any' type. Use specific types or 'unknown' instead."
    fi

    # Check 3: Hardcoded secrets (basic check)
    if grep -niE "(api_key|apikey|secret|password|token)\s*=\s*['\"][^'\"]+['\"]" "$file" > /dev/null 2>&1; then
        line=$(grep -niE "(api_key|apikey|secret|password|token)\s*=\s*['\"][^'\"]+['\"]" "$file" | head -1 | cut -d: -f1)
        report_issue "critical" "$file" "$line" "Potential hardcoded secret detected. Use environment variables."
    fi

    # Check 4: dangerouslySetInnerHTML usage
    if grep -n "dangerouslySetInnerHTML" "$file" > /dev/null 2>&1; then
        line=$(grep -n "dangerouslySetInnerHTML" "$file" | head -1 | cut -d: -f1)
        report_issue "critical" "$file" "$line" "Using dangerouslySetInnerHTML can lead to XSS. Ensure proper sanitization."
    fi

    # Check 5: Inline styles
    if grep -n "style={{" "$file" > /dev/null 2>&1; then
        line=$(grep -n "style={{" "$file" | head -1 | cut -d: -f1)
        report_issue "warning" "$file" "$line" "Avoid inline styles. Use Tailwind CSS classes instead."
    fi

    # Check 6: Console logs (should be removed in production code)
    if grep -n "console\\.log" "$file" > /dev/null 2>&1; then
        line=$(grep -n "console\\.log" "$file" | head -1 | cut -d: -f1)
        report_issue "info" "$file" "$line" "Remove console.log statements before committing."
    fi

    # Check 7: TODO comments
    if grep -n "TODO" "$file" > /dev/null 2>&1; then
        line=$(grep -n "TODO" "$file" | head -1 | cut -d: -f1)
        report_issue "info" "$file" "$line" "TODO comment found. Consider creating a GitHub issue."
    fi

    # Check 8: Missing key prop in map
    if grep -n "\.map(" "$file" > /dev/null 2>&1; then
        # This is a simplified check - would need more sophisticated parsing
        if ! grep -A 3 "\.map(" "$file" | grep -q "key="; then
            line=$(grep -n "\.map(" "$file" | head -1 | cut -d: -f1)
            report_issue "warning" "$file" "$line" "Ensure .map() returns elements with 'key' prop."
        fi
    fi

    # Check 9: Component naming in TSX files
    if [[ "$file" == *.tsx ]]; then
        # Check if there's a function component defined
        if grep -n "^export default function" "$file" > /dev/null 2>&1; then
            func_line=$(grep -n "^export default function" "$file" | head -1)
            func_name=$(echo "$func_line" | sed -E 's/.*function\s+([A-Za-z0-9_]+).*/\1/')

            # Component name should be PascalCase
            if [[ ! "$func_name" =~ ^[A-Z][a-zA-Z0-9]*$ ]]; then
                line=$(echo "$func_line" | cut -d: -f1)
                report_issue "warning" "$file" "$line" "Component name should be PascalCase: $func_name"
            fi
        fi
    fi

    # Check 10: Import organization (simplified check)
    if grep -n "^import" "$file" > /dev/null 2>&1; then
        # Check if React import is at the top (after CSS)
        first_import_line=$(grep -n "^import.*from.*react" "$file" | head -1 | cut -d: -f1)
        css_import_line=$(grep -n "^import.*\.css" "$file" | head -1 | cut -d: -f1)

        if [ -n "$first_import_line" ] && [ -n "$css_import_line" ]; then
            if [ "$first_import_line" -lt "$css_import_line" ]; then
                report_issue "info" "$file" "$first_import_line" "CSS imports should come before React imports."
            fi
        fi
    fi

done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Review Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${RED}🔴 Critical Issues: $CRITICAL${NC}"
echo -e "${YELLOW}🟡 Warnings: $WARNING${NC}"
echo -e "${BLUE}🔵 Info: $INFO${NC}"
echo ""

# Determine overall status
if [ $CRITICAL -gt 0 ]; then
    echo -e "${RED}❌ Review Failed${NC}"
    echo "Please fix critical issues before proceeding."
    exit 1
elif [ $WARNING -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Review Passed with Warnings${NC}"
    echo "Consider addressing warnings for better code quality."
    exit 0
else
    echo -e "${GREEN}✅ Review Passed${NC}"
    echo "Code follows GlycoGrit standards!"
    exit 0
fi
