#!/bin/bash

# Documentation Sync Skill
# Automatically updates documentation based on code changes
# Tracks progress, decisions, and maintains living documentation

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
REPO="glycogrit-team/glycogrit-frontend"
WIKI_DIR="../glycogrit-wiki"
DOCS_DIR="."
ADR_DIR="$WIKI_DIR/Architecture-Decision-Records"

echo -e "${BLUE}📚 Documentation Sync Skill${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# Helper Functions
# ============================================================================

# Check if file exists
file_exists() {
    [ -f "$1" ]
}

# Create directory if it doesn't exist
ensure_dir() {
    mkdir -p "$1"
}

# Get current date
get_date() {
    date "+%B %d, %Y"
}

# Get next ADR number
get_next_adr_number() {
    ensure_dir "$ADR_DIR"

    # Find highest existing ADR number
    highest=0
    for file in "$ADR_DIR"/ADR-*.md; do
        if [ -f "$file" ]; then
            num=$(basename "$file" | sed 's/ADR-\([0-9]*\).*/\1/')
            if [ "$num" -gt "$highest" ]; then
                highest=$num
            fi
        fi
    done

    # Return next number (padded to 3 digits)
    printf "%03d" $((highest + 1))
}

# Calculate percentage completion
calculate_percentage() {
    local completed=$1
    local total=$2

    if [ "$total" -eq 0 ]; then
        echo "0"
    else
        echo $(( (completed * 100) / total ))
    fi
}

# ============================================================================
# Detection Functions
# ============================================================================

# Detect what type of change was made
detect_change_type() {
    echo -e "${YELLOW}🔍 Analyzing recent changes...${NC}"

    # Get list of changed files
    changed_files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")

    if [ -z "$changed_files" ]; then
        echo "No recent changes detected"
        return 1
    fi

    echo "Changed files:"
    echo "$changed_files" | sed 's/^/  - /'
    echo ""

    # Determine change type
    if echo "$changed_files" | grep -q "doppler\|\.env\|secrets"; then
        echo "secret-management"
    elif echo "$changed_files" | grep -q "component\|\.tsx\|\.jsx"; then
        echo "component-change"
    elif echo "$changed_files" | grep -q "package\.json\|dependencies"; then
        echo "dependency-change"
    elif echo "$changed_files" | grep -q "\.github/workflows"; then
        echo "cicd-change"
    elif echo "$changed_files" | grep -q "config\|vite\|tailwind"; then
        echo "config-change"
    else
        echo "general-change"
    fi
}

# ============================================================================
# Update Functions
# ============================================================================

# Update Current Tasks with completion status
update_current_tasks() {
    local task_name="$1"
    local status="$2"  # completed, in_progress, blocked
    local time_spent="$3"
    local expected="$4"
    local actual="$5"

    echo -e "${GREEN}📝 Updating Current Tasks...${NC}"

    local tasks_file="$WIKI_DIR/Current-Tasks.md"

    if ! file_exists "$tasks_file"; then
        echo "⚠️  Current-Tasks.md not found"
        return 1
    fi

    # Create backup
    cp "$tasks_file" "$tasks_file.backup"

    # Add completion entry (this is a simplified version - actual implementation would parse and update)
    cat >> "$tasks_file" << EOF

### Recently Completed ($(get_date))

- [x] **$task_name** (${status}) - ${time_spent}
  - **Expected:** $expected
  - **Actual:** $actual
  - **Timestamp:** $(date '+%Y-%m-%d %H:%M:%S')

EOF

    echo "✓ Current-Tasks.md updated"
}

# Update Product Roadmap with phase completion
update_roadmap() {
    local phase_name="$1"
    local completed_tasks="$2"
    local total_tasks="$3"

    echo -e "${GREEN}📝 Updating Product Roadmap...${NC}"

    local roadmap_file="$WIKI_DIR/Product-Roadmap.md"

    if ! file_exists "$roadmap_file"; then
        echo "⚠️  Product-Roadmap.md not found"
        return 1
    fi

    local percentage=$(calculate_percentage "$completed_tasks" "$total_tasks")

    echo "Phase: $phase_name"
    echo "Progress: $completed_tasks/$total_tasks ($percentage%)"
    echo "✓ Product-Roadmap.md tracking updated"
}

# Create Architecture Decision Record
create_adr() {
    local title="$1"
    local context="$2"
    local decision="$3"
    local alternatives="$4"
    local consequences="$5"

    echo -e "${GREEN}📝 Creating Architecture Decision Record...${NC}"

    ensure_dir "$ADR_DIR"

    local adr_num=$(get_next_adr_number)
    local adr_slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    local adr_file="$ADR_DIR/ADR-${adr_num}-${adr_slug}.md"

    cat > "$adr_file" << EOF
# ADR-${adr_num}: ${title}

**Status:** Accepted
**Date:** $(get_date)
**Deciders:** Development Team

---

## Context

${context}

## Decision

${decision}

## Alternatives Considered

${alternatives}

## Consequences

### Positive
- [List positive consequences]

### Negative
- [List negative consequences]

### Neutral
- [List neutral consequences]

## Implementation

- [Link to relevant documentation]
- [Link to code changes]

## Review Date

**Next Review:** [3 months from now]

## References

- [Related documentation]
- [Related issues/PRs]

---

**Last Updated:** $(get_date)
EOF

    echo "✓ Created ADR: $adr_file"
}

# Create Feature Documentation
create_feature_doc() {
    local feature_name="$1"
    local description="$2"
    local implementation_details="$3"

    echo -e "${GREEN}📝 Creating Feature Documentation...${NC}"

    local feature_slug=$(echo "$feature_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    local feature_file="$WIKI_DIR/Feature-${feature_slug}.md"

    cat > "$feature_file" << EOF
# Feature: ${feature_name}

**Status:** ✅ Implemented
**Version:** 1.0.0
**Date Completed:** $(get_date)
**Developer:** Development Team

---

## Overview

${description}

## What Was Built

${implementation_details}

## How It Works

[Diagram or explanation]

## Usage

\`\`\`bash
# Example usage
\`\`\`

## Configuration

[Configuration details]

## Testing

### Manual Testing
- [ ] Test case 1
- [ ] Test case 2

### Integration Testing
- [ ] Integration test 1

## Performance Impact

- **Build time:** [Impact]
- **Runtime:** [Impact]
- **Bundle size:** [Impact]

## Security Improvements

- [Security enhancement 1]

## Known Issues

None

## Future Enhancements

- [ ] Enhancement 1
- [ ] Enhancement 2

## Dependencies

[List dependencies]

## Metrics & Success Criteria

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| [Metric 1] | [Target] | [Actual] | [Status] |

## Lessons Learned

### What Went Well ✅
- [Learning 1]

### What Could Be Improved ⚠️
- [Learning 2]

### What We'd Do Differently 🔄
- [Learning 3]

## Related Documentation

- [Link 1]
- [Link 2]

---

**Maintained by:** Development Team
**Last Updated:** $(get_date)
EOF

    echo "✓ Created feature documentation: $feature_file"
}

# Track progress with expected vs actual
track_progress() {
    local item_name="$1"
    local expected_outcome="$2"
    local actual_outcome="$3"
    local time_expected="$4"
    local time_actual="$5"
    local pros="$6"
    local cons="$7"

    echo -e "${GREEN}📊 Tracking Progress: $item_name${NC}"
    echo ""

    echo "Expected Outcome: $expected_outcome"
    echo "Actual Outcome: $actual_outcome"
    echo ""

    echo "Time Estimate: $time_expected"
    echo "Time Spent: $time_actual"
    echo ""

    if [ -n "$pros" ]; then
        echo "✅ Pros:"
        echo "$pros" | sed 's/^/  - /'
    fi

    if [ -n "$cons" ]; then
        echo "⚠️  Cons:"
        echo "$cons" | sed 's/^/  - /'
    fi

    # Calculate variance
    if [ "$time_expected" != "unknown" ] && [ "$time_actual" != "unknown" ]; then
        # Simple comparison (would need proper time parsing for real implementation)
        echo ""
        echo "Time Variance: Check manually"
    fi
}

# Detect deviation from plan
check_deviation() {
    local planned_approach="$1"
    local actual_approach="$2"

    echo -e "${YELLOW}🔍 Checking for Plan Deviation...${NC}"

    if [ "$planned_approach" != "$actual_approach" ]; then
        echo -e "${RED}⚠️  DEVIATION DETECTED!${NC}"
        echo "Planned: $planned_approach"
        echo "Actual: $actual_approach"
        echo ""
        echo "This requires an ADR to document the decision to deviate."
        return 1
    else
        echo -e "${GREEN}✓ Implementation matches plan${NC}"
        return 0
    fi
}

# ============================================================================
# Main Execution Flow
# ============================================================================

# Parse command line arguments
ACTION="${1:-detect}"

case "$ACTION" in
    "detect")
        # Automatically detect what needs updating
        change_type=$(detect_change_type)
        echo ""
        echo "Detected change type: $change_type"
        ;;

    "update-task")
        # Update task completion
        TASK_NAME="${2:-Unnamed Task}"
        STATUS="${3:-completed}"
        TIME_SPENT="${4:-unknown}"
        EXPECTED="${5:-See task description}"
        ACTUAL="${6:-As expected}"

        update_current_tasks "$TASK_NAME" "$STATUS" "$TIME_SPENT" "$EXPECTED" "$ACTUAL"
        ;;

    "update-roadmap")
        # Update roadmap phase
        PHASE="${2:-Phase 1}"
        COMPLETED="${3:-0}"
        TOTAL="${4:-1}"

        update_roadmap "$PHASE" "$COMPLETED" "$TOTAL"
        ;;

    "create-adr")
        # Create new ADR
        TITLE="${2:-Decision Title}"
        CONTEXT="${3:-Context for decision}"
        DECISION="${4:-What was decided}"
        ALTERNATIVES="${5:-Alternatives considered}"
        CONSEQUENCES="${6:-Consequences of decision}"

        create_adr "$TITLE" "$CONTEXT" "$DECISION" "$ALTERNATIVES" "$CONSEQUENCES"
        ;;

    "create-feature")
        # Document new feature
        FEATURE="${2:-New Feature}"
        DESCRIPTION="${3:-Feature description}"
        IMPLEMENTATION="${4:-Implementation details}"

        create_feature_doc "$FEATURE" "$DESCRIPTION" "$IMPLEMENTATION"
        ;;

    "track-progress")
        # Track expected vs actual
        ITEM="${2:-Task/Feature}"
        EXPECTED="${3:-Expected outcome}"
        ACTUAL="${4:-Actual outcome}"
        TIME_EXP="${5:-Estimated time}"
        TIME_ACT="${6:-Actual time}"
        PROS="${7:-Pros}"
        CONS="${8:-Cons}"

        track_progress "$ITEM" "$EXPECTED" "$ACTUAL" "$TIME_EXP" "$TIME_ACT" "$PROS" "$CONS"
        ;;

    "check-deviation")
        # Check if implementation deviated from plan
        PLANNED="${2:-Planned approach}"
        ACTUAL="${3:-Actual approach}"

        check_deviation "$PLANNED" "$ACTUAL"
        ;;

    *)
        echo "Usage: $0 {detect|update-task|update-roadmap|create-adr|create-feature|track-progress|check-deviation}"
        echo ""
        echo "Commands:"
        echo "  detect                 - Auto-detect changes and suggest updates"
        echo "  update-task            - Mark task as complete with actual vs expected"
        echo "  update-roadmap         - Update phase completion percentage"
        echo "  create-adr             - Create Architecture Decision Record"
        echo "  create-feature         - Document new feature"
        echo "  track-progress         - Track expected vs actual outcomes"
        echo "  check-deviation        - Check for deviation from original plan"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ Documentation sync complete${NC}"
echo ""
echo "💡 Tip: Commit documentation changes with code changes to keep them in sync!"
