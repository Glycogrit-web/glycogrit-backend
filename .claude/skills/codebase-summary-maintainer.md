# Codebase Summary Maintainer

Automatically maintain CODEBASE_SUMMARY.md by detecting code changes and updating only relevant sections.

## Usage

```bash
# Default: Detect changes and update with confirmation
/update-codebase-summary

# Show what would change without updating
/update-codebase-summary --dry-run

# Update specific section only
/update-codebase-summary --section backend
/update-codebase-summary --section frontend
```

## How It Works

### Phase 1: Change Detection

1. Check for recent file changes using git:
   ```bash
   git diff --name-only HEAD~5 HEAD    # Recent commits
   git status --short                  # Unstaged changes
   ```

2. If no git repository, fallback to analyzing specified files

3. Classify changed files by path:
   - `glycogrit-backend/app/models/` → Backend Models section
   - `glycogrit-backend/app/services/` → Backend Services section
   - `glycogrit-backend/app/api/` → Backend API Routes section
   - `glycogrit-frontend/src/pages/` → Frontend Pages section
   - `glycogrit-frontend/src/components/features/` → Frontend Feature Components
   - `glycogrit-frontend/src/lib/` → Frontend Core Library
   - Config files → Configuration section

### Phase 2: File Analysis

For each changed file:

1. **Extract Documentation**:
   - Python: Read module docstring (first `"""..."""` block)
   - TypeScript: Read JSDoc comments or file-level comments
   - If no documentation: Infer purpose from class/function names

2. **Get File Metadata**:
   ```bash
   ls -lh <file>     # File size
   wc -l <file>      # Line count
   ```

3. **Note Size** if file is large:
   - > 20KB → "(20KB)"
   - > 30KB → "(30KB)"
   - > 40KB → "(40KB - largest file)"

4. **Generate Description** using consistent patterns:
   - Services: "[Action verb] [entity] [context]"
     - Example: "Validates tier upgrade eligibility and processes payment"
   - Components: "[UI element] for [purpose]"
     - Example: "Card component for displaying event tier options"
   - APIs: "[HTTP methods] for [resource]"
     - Example: "CRUD endpoints for event management"

### Phase 3: Preview Changes (Manual Confirmation Mode)

1. Show affected sections:
   ```
   📝 Planned updates:

   Backend Services section:
     - registration_service.py: Description unchanged, size updated (40KB → 42KB)

   Frontend Pages section:
     - EventCheckout.tsx: Description updated + size changed (29KB → 32KB)

   Frontend Feature Components section:
     + TierUpgrade.tsx: NEW - "Component for upgrading event registration tier"
   ```

2. Ask user: "Apply these updates to CODEBASE_SUMMARY.md? (y/n)"

3. If yes → proceed to update
   If no → cancel and exit

### Phase 4: Update Execution

1. Parse existing CODEBASE_SUMMARY.md to extract sections

2. For each affected section:
   - Locate section by heading (e.g., `### Business Logic Services`)
   - Find file entry (e.g., `- **registration_service.py**`)
   - Update description and/or size annotation
   - Add new entries in alphabetical order
   - Remove entries for deleted files
   - Preserve markdown formatting

3. Update timestamp in header:
   ```markdown
   > **Last Updated**: [current date]
   ```

4. Write updated content back to CODEBASE_SUMMARY.md

### Phase 5: Report Results

Show summary:
```
✅ Updated CODEBASE_SUMMARY.md
  - 3 sections modified
  - 1 entry added
  - 2 entries updated
  - Total: 425 lines (within 500 limit)

Next: git add CODEBASE_SUMMARY.md && git commit -m "docs: Update codebase summary"
```

## Section Detection Rules

```
Path Pattern                                    → Section to Update
─────────────────────────────────────────────────────────────────────
glycogrit-backend/app/core/                    → Core Infrastructure
glycogrit-backend/app/models/                  → Database Models
glycogrit-backend/app/services/                → Business Logic Services
glycogrit-backend/app/api/                     → API Routes
glycogrit-backend/app/repositories/            → Data Access Layer
glycogrit-backend/app/schemas/                 → Validation Schemas
glycogrit-backend/requirements.txt             → Backend Configuration
glycogrit-backend/alembic.ini                  → Backend Configuration
glycogrit-backend/Dockerfile                   → Backend Configuration

glycogrit-frontend/src/lib/                    → Core Library
glycogrit-frontend/src/pages/                  → Page Components
glycogrit-frontend/src/components/features/    → Feature Components
glycogrit-frontend/src/components/common/      → Common Components
glycogrit-frontend/src/contexts/               → State Management
glycogrit-frontend/src/hooks/                  → Custom Hooks
glycogrit-frontend/package.json                → Frontend Configuration
glycogrit-frontend/vite.config.ts              → Frontend Configuration
```

## Description Generation Patterns

### Python Services
Pattern: "[Action verb] [entity/operation] [additional context]"

Examples:
- "Validates tier upgrade eligibility and processes payment"
- "Creates payment orders via Razorpay gateway"
- "Manages event registration with tier selection"
- "Handles user authentication and OAuth flow"
- "Optimizes and uploads images to Cloudflare R2"

### TypeScript Components
Pattern: "[UI element type] for [primary purpose]"

Examples:
- "Card component for displaying event tier options"
- "Modal for tier upgrade selection and payment"
- "Form for user profile editing with validation"
- "Grid layout for activity category selection"
- "Upload component for activity proof images"

### API Modules
Pattern: "[Primary endpoints] for [resource management]"

Examples:
- "CRUD endpoints for event management"
- "Authentication endpoints (login, signup, OAuth)"
- "Payment order creation and verification"
- "Tier-based registration and upgrade endpoints"

### Configuration Files
Pattern: "[Tool/Framework] [configuration type]"

Examples:
- "Vite build tool configuration"
- "TypeScript compiler options"
- "Tailwind CSS customization"
- "Alembic database migration configuration"

## Edge Cases

### No Changes Detected
```
🔍 Analyzing codebase changes...
ℹ️  No file changes detected since last update.
CODEBASE_SUMMARY.md is already up to date.
```

### File Deleted
- Remove file entry from appropriate section
- Update section if it was referenced in workflows

### File Renamed
- Detect as deleted + new file
- Update all references in the summary

### No Git Repository
- Fallback to file timestamp comparison
- Analyze all specified files
- Recommend using git for better change tracking

### Large Structural Changes
```
⚠️  Detected 50+ file changes across multiple sections.
This appears to be a major refactor.

Recommendation: Perform a full review of CODEBASE_SUMMARY.md
manually to ensure all changes are accurately reflected.

Continue with automatic update? (y/n):
```

### File Without Documentation
- Attempt to infer purpose from:
  - File name and location
  - Class/function names
  - Import statements
- Add "(TODO: Add description)" marker if ambiguous
- Flag for manual review in report

### Summary Exceeds Size Limit
```
⚠️  Updated summary is 520 lines (target: 500 lines)

Consider:
1. Consolidating similar entries
2. Moving detailed info to dedicated docs
3. Focusing on essential files only

Apply updates anyway? (y/n):
```

## Integration with Git Workflow

### Typical Developer Workflow

```bash
# 1. Make code changes to backend service
vim glycogrit-backend/app/services/new_feature_service.py

# 2. Run tests
pytest

# 3. Stage changes
git add glycogrit-backend/app/services/new_feature_service.py

# 4. Update codebase summary
/update-codebase-summary

# 5. Review changes and confirm
# (Skill shows preview and asks for confirmation)

# 6. Commit everything together
git add CODEBASE_SUMMARY.md
git commit -m "feat: Add new feature service with updated docs"
```

### Optional Git Hooks

Add to `.git/hooks/pre-commit` for automatic checks:
```bash
#!/bin/sh
# Check if code files changed
if git diff --cached --name-only | grep -qE '\.(py|ts|tsx)$'; then
  echo "Code files changed. Consider running:"
  echo "  /update-codebase-summary"
fi
```

## Command Options

### Default Mode (with confirmation)
```bash
/update-codebase-summary
```
- Detects changes automatically via git
- Shows preview of updates
- Asks for confirmation before applying
- Reports summary of changes

### Dry Run Mode
```bash
/update-codebase-summary --dry-run
```
- Shows what would be updated
- Does NOT modify CODEBASE_SUMMARY.md
- Useful for previewing changes before committing

### Section-Specific Update
```bash
/update-codebase-summary --section backend
/update-codebase-summary --section frontend
/update-codebase-summary --section workflows
```
- Updates only the specified section
- Faster for targeted changes
- Still shows preview and asks for confirmation

## Behavior Examples

### Example 1: New Service Added

**Change**: Created `glycogrit-backend/app/services/notification_service.py`

**Skill Output**:
```
🔍 Analyzing codebase changes...
Found 1 new file:
  + glycogrit-backend/app/services/notification_service.py

📝 Extracting information...
  ✓ Read notification_service.py (8KB)
  ✓ Found docstring: "Handles email and push notification delivery"

📝 Planned updates:

  Backend Services section:
    + notification_service.py - "Handles email and push notification delivery"

Apply updates? (y/n): y

✅ Updated CODEBASE_SUMMARY.md
  - 1 section modified
  - 1 entry added
  - Total: 387 lines

Next: git add CODEBASE_SUMMARY.md && git commit -m "docs: Add notification service to summary"
```

### Example 2: Component Size Changed

**Change**: Modified `glycogrit-frontend/src/pages/EventCheckout.tsx` (grew from 29KB to 34KB)

**Skill Output**:
```
🔍 Analyzing codebase changes...
Found 1 modified file:
  - glycogrit-frontend/src/pages/EventCheckout.tsx

📝 Extracting information...
  ✓ Read EventCheckout.tsx (34KB, was 29KB)
  ✓ Description still accurate

📝 Planned updates:

  Frontend Pages section:
    - EventCheckout.tsx: Size updated (29KB → 34KB)

Apply updates? (y/n): y

✅ Updated CODEBASE_SUMMARY.md
  - 1 section modified
  - 1 entry updated
  - Total: 392 lines
```

### Example 3: Multiple Changes

**Changes**:
- Modified backend service
- Added new frontend component
- Updated configuration

**Skill Output**:
```
🔍 Analyzing codebase changes...
Found 3 changed files:
  - glycogrit-backend/app/services/payment_service.py
  + glycogrit-frontend/src/components/features/RefundRequest.tsx
  - glycogrit-backend/requirements.txt

📝 Extracting information...
  ✓ Read payment_service.py (30KB)
  ✓ Read RefundRequest.tsx (6KB)
  ✓ Read requirements.txt

📝 Planned updates:

  Backend Services section:
    - payment_service.py: Description updated
      Old: "Payment order creation via Razorpay, signature verification, refund processing"
      New: "Payment order creation, verification, refund processing with automated retry"

  Frontend Feature Components section:
    + RefundRequest.tsx - "Modal form for requesting payment refunds"

  Backend Configuration section:
    - requirements.txt: Updated dependencies (added celery)

Apply updates? (y/n): y

✅ Updated CODEBASE_SUMMARY.md
  - 3 sections modified
  - 1 entry added
  - 2 entries updated
  - Total: 395 lines
```

### Example 4: Dry Run

```bash
$ /update-codebase-summary --dry-run

🔍 Analyzing codebase changes...
Found 2 modified files:
  - glycogrit-backend/app/api/events.py
  - glycogrit-frontend/src/pages/Dashboard.tsx

📝 Planned updates (DRY RUN - no changes will be made):

  Backend API Routes section:
    - events.py: Description unchanged

  Frontend Pages section:
    - Dashboard.tsx: Size updated (12KB → 14KB)

Would update: 2 sections, 2 entries modified
No changes applied (dry run mode).
```

## Maintenance Recommendations

### When to Run

**Always run after**:
- Adding new services, components, or API routes
- Significant refactoring (file renames, structural changes)
- Major feature additions

**Consider running after**:
- Modifying existing files (if description changed)
- Updating configuration files
- Adding new workflows

**Monthly**:
- Full manual review of CODEBASE_SUMMARY.md
- Ensure accuracy and completeness
- Trim unnecessary details if over 500 lines

### What to Review Manually

- Workflow sections (may need manual updates for new processes)
- Architecture patterns (may need updates for new patterns)
- File descriptions (verify auto-generated descriptions are accurate)
- Size annotations (ensure large files are noted)

### Skill Maintenance

If codebase structure changes significantly:
1. Update section detection rules in skill documentation
2. Adjust description generation patterns
3. Add new file type handlers
4. Test with various change scenarios

## Limitations

1. **Cannot detect semantic changes**: Only detects file-level changes, not subtle logic changes within functions
2. **Limited inference**: Without good documentation, may generate generic descriptions
3. **Markdown only**: Only maintains CODEBASE_SUMMARY.md, not other documentation
4. **Git dependency**: Works best with git; fallback mode is less accurate
5. **Manual review needed**: Auto-generated content should always be reviewed before committing

## Benefits

1. **Keeps documentation fresh**: Summary stays synchronized with code
2. **Saves time**: Automates tedious documentation updates
3. **Consistent format**: Maintains uniform structure and style
4. **Prevents drift**: Reduces chance of documentation becoming outdated
5. **Easy to use**: Simple command with clear feedback
6. **Safe**: Manual confirmation prevents unwanted changes

---

**Version**: 1.0.0
**Last Updated**: May 2025
**Maintainer**: Claude Code
