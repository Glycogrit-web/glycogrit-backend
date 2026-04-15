# Wiki Updater Skill

**Purpose**: Automatically detect significant code changes and propose updates to the project wiki.

## When to Trigger

This skill should be invoked when:

1. **Design Pattern Changes**
   - New repository pattern implementations
   - New dependency injection patterns
   - Service layer modifications
   - Database access patterns

2. **API Changes**
   - New endpoints added
   - Endpoint modifications
   - New authentication requirements
   - Request/response schema changes

3. **Security Implementations**
   - New authentication mechanisms
   - Authorization rules
   - Security middleware
   - Input validation patterns

4. **Database Schema Changes**
   - New models added
   - Model relationship changes
   - Migration patterns

5. **Configuration Changes**
   - New environment variables
   - Settings modifications
   - Feature flags

## Detection Patterns

### Pattern 1: New API Endpoints
```python
# Detect: @router.get(), @router.post(), etc.
@router.post("/api/v1/...")
```
**Action**: Update API documentation wiki page

### Pattern 2: New Models
```python
# Detect: New SQLAlchemy models
class NewModel(Base):
    __tablename__ = "..."
```
**Action**: Update database schema documentation

### Pattern 3: New Schemas
```python
# Detect: New Pydantic schemas
class NewSchema(BaseModel):
    ...
```
**Action**: Update API schemas documentation

### Pattern 4: Authentication Changes
```python
# Detect: Changes in auth.py, firebase.py, middleware/auth.py
```
**Action**: Update security documentation

### Pattern 5: Configuration Changes
```python
# Detect: Changes in core/config.py
class Settings(BaseSettings):
    new_setting: str
```
**Action**: Update configuration documentation

## Wiki Pages to Update

| Change Type | Wiki Page | Location |
|-------------|-----------|----------|
| API Endpoints | `API-Documentation.md` | Root |
| Database Models | `Database-Schema.md` | Root |
| Security | `Security-Best-Practices.md` | Root |
| Configuration | `Configuration-Guide.md` | Root |
| Design Patterns | `Design-Patterns.md` | Root |
| Deployment | `DEPLOYMENT.md` | Root |

## Workflow

### 1. Detection Phase
```bash
# Check for significant changes
git diff --name-status | grep -E "(app/api|app/models|app/schemas|app/core|app/middleware)"
```

### 2. Analysis Phase
- Identify change type
- Determine affected wiki pages
- Extract relevant code snippets
- Generate update proposal

### 3. Proposal Phase
Present the proposed changes to the user:
```markdown
## Proposed Wiki Update

**File Changed**: app/api/v1/endpoints/rides.py
**Change Type**: New API Endpoint
**Wiki Page**: API-Documentation.md

**Proposed Addition**:
### POST /api/v1/rides/{ride_id}/join
Join a ride as a participant.

**Request Body**:
- None (authenticated user automatically added)

**Response**: RideResponse with updated participants list
```

### 4. Application Phase (Manual Approval Required)
- User reviews proposal
- User approves or modifies
- Apply changes to wiki
- Log update in `.claude/wiki-updates/`

## Usage

### Automatic Trigger
The skill automatically checks for updates after:
- Git commits
- File saves in watched directories
- Manual invocation

### Manual Trigger
```bash
# Run wiki updater
claude skill wiki-updater
```

### Configuration
Edit `.claude/wiki-updater.config.json` to customize:
- Watch patterns
- Wiki page mappings
- Auto-detection rules
- Approval requirements

## Safety Features

### Dry Run Mode
```bash
# Preview changes without applying
claude skill wiki-updater --dry-run
```

### Diff Preview
Always show a diff before applying changes:
```diff
+ ### POST /api/v1/rides/{ride_id}/join
+ Join a ride as a participant.
```

### Rollback Support
Track all changes in `.claude/wiki-updates/history.json`:
```json
{
  "timestamp": "2026-04-15T18:30:00Z",
  "file": "API-Documentation.md",
  "type": "addition",
  "change": "..."
}
```

## Example Scenarios

### Scenario 1: New API Endpoint Added
**Change**: Added `POST /api/v1/events/{event_id}/register`

**Detection**:
- File: `app/api/v1/endpoints/events.py`
- Pattern: `@router.post("/api/v1/events/{event_id}/register")`

**Action**:
1. Extract endpoint definition
2. Extract docstring
3. Extract request/response schemas
4. Generate documentation
5. Propose addition to `API-Documentation.md`

### Scenario 2: New Database Model
**Change**: Added `Challenge` model

**Detection**:
- File: `app/models/challenge.py`
- Pattern: `class Challenge(Base):`

**Action**:
1. Extract model fields
2. Extract relationships
3. Generate schema diagram
4. Propose addition to `Database-Schema.md`

### Scenario 3: Security Middleware Updated
**Change**: Added rate limiting middleware

**Detection**:
- File: `app/middleware/rate_limit.py`
- Pattern: New middleware class

**Action**:
1. Extract middleware logic
2. Document configuration
3. Propose addition to `Security-Best-Practices.md`

## Best Practices

1. **Always review proposals** before applying
2. **Keep wiki pages in sync** with code
3. **Document breaking changes** prominently
4. **Update examples** when APIs change
5. **Track decision rationale** in ADRs
6. **Version documentation** alongside code

## Configuration File

See `.claude/wiki-updater.config.json` for:
- Watch patterns
- Wiki page mappings
- Detection rules
- Auto-approval settings (default: false)

## Logging

All wiki updates are logged to:
- `.claude/wiki-updates/history.json` - Change history
- `.claude/wiki-updates/pending.json` - Pending proposals
- `.claude/wiki-updates/applied.json` - Applied changes

## Notes

- **Requires user approval** by default for safety
- **Does not commit changes** automatically
- **Supports rollback** for the last 10 changes
- **Conflict detection** if wiki edited externally
- **Pattern matching** can be customized per project
