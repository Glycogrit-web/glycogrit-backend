# Documentation Sync Skill

**Purpose**: Automatically synchronize documentation with code changes to maintain living documentation.

## What This Skill Does

1. **Tracks Project Progress**
   - Updates task completion status
   - Maintains roadmap alignment
   - Tracks feature implementation

2. **Creates Architecture Decision Records (ADRs)**
   - Documents major technical decisions
   - Records rationale and alternatives
   - Tracks consequences and trade-offs

3. **Updates Feature Documentation**
   - Auto-generates API endpoint docs
   - Updates model documentation
   - Syncs schema definitions

4. **Maintains Task Lists**
   - Updates `Current-Tasks.md`
   - Syncs with `Product-Roadmap.md`
   - Tracks completion percentages

## Automatic Updates

### Task Completion Tracking
```markdown
## Backend API Development

**Status**: 🟡 In Progress (65% complete)

### Completed ✅
- [x] User authentication with Firebase
- [x] Basic CRUD for rides
- [x] PostgreSQL database setup
- [x] Docker containerization

### In Progress 🚧
- [ ] Event management endpoints (80% complete)
- [ ] File upload for ride photos (40% complete)

### Planned 📋
- [ ] Social features (likes, comments)
- [ ] Push notifications
```

### ADR Creation
When significant architectural decisions are made, automatically create ADR:

**Trigger Examples**:
- Choosing authentication method
- Selecting database ORM
- Deciding API versioning strategy
- Picking deployment platform

**ADR Template**:
```markdown
# ADR-001: Use Firebase Authentication

**Date**: 2026-04-15
**Status**: Accepted
**Context**: Need user authentication for GlycoGrit backend

## Decision
Use Firebase Authentication with JWT token validation on backend.

## Rationale
- Frontend already uses Firebase
- No need to manage user credentials
- Built-in email verification
- Social login support
- Free tier sufficient for 10K users

## Alternatives Considered
1. **Custom JWT auth**: More control, but more maintenance
2. **Auth0**: Feature-rich but expensive ($23/month)
3. **Supabase Auth**: Good option but adds dependency

## Consequences
**Positive**:
- Reduced backend complexity
- Better security (Firebase handles passwords)
- Faster development

**Negative**:
- Vendor lock-in to Firebase
- Need to validate Firebase tokens on every request
- Limited customization of auth flow

## Implementation Notes
- Validate Firebase JWT on backend using Firebase Admin SDK
- Store user profile data in PostgreSQL
- Map Firebase UID to internal user ID
```

### Feature Documentation Updates
When new features are added, create/update documentation:

```markdown
# Ride Management Feature

## Overview
Allows users to create, join, and manage group rides.

## API Endpoints
- `POST /api/v1/rides/` - Create new ride
- `GET /api/v1/rides/` - List all rides
- `GET /api/v1/rides/{id}` - Get ride details
- `PUT /api/v1/rides/{id}` - Update ride
- `DELETE /api/v1/rides/{id}` - Delete ride
- `POST /api/v1/rides/{id}/join` - Join ride

## Database Schema
```python
class Ride(Base):
    id: UUID
    title: str
    description: str
    organizer_id: UUID
    start_time: datetime
    distance_km: float
    difficulty: str
    max_participants: int
```

## Implementation Status
- ✅ Basic CRUD operations
- ✅ User authorization
- 🚧 Photo uploads (in progress)
- 📋 Route mapping (planned)
```

## Documentation Files Managed

| File | Purpose | Update Trigger |
|------|---------|----------------|
| `Current-Tasks.md` | Active development tasks | Task completion, new tasks |
| `Product-Roadmap.md` | Feature roadmap | Milestone completion |
| `ADRs/*.md` | Architecture decisions | Major technical decisions |
| `API-Documentation.md` | API reference | New endpoints |
| `Database-Schema.md` | Database structure | Model changes |
| `CHANGELOG.md` | Version history | Releases |

## Usage

### Automatic Mode (Recommended)
The skill runs automatically after:
- Git commits
- Significant code changes
- Feature completion

### Manual Invocation
```bash
# Sync all documentation
claude skill doc-sync

# Sync specific type
claude skill doc-sync --type=tasks
claude skill doc-sync --type=adr
claude skill doc-sync --type=features
```

### Create ADR
```bash
# Create new ADR
claude skill doc-sync --create-adr "Use PostgreSQL for database"
```

## Configuration

Edit `.claude/doc-sync.config.json`:

```json
{
  "enabled": true,
  "auto_sync": true,
  "watch_files": [
    "app/**/*.py",
    "alembic/versions/*.py",
    "requirements.txt"
  ],
  "task_tracking": {
    "enabled": true,
    "files": ["Current-Tasks.md", "Product-Roadmap.md"],
    "completion_percentage": true
  },
  "adr": {
    "enabled": true,
    "directory": "docs/adr/",
    "auto_create": false,
    "template": "adr-template.md"
  },
  "changelog": {
    "enabled": true,
    "file": "CHANGELOG.md",
    "format": "keep-a-changelog"
  }
}
```

## Progress Tracking

### Completion Percentage Calculation
```python
def calculate_completion(tasks):
    total = len(tasks)
    completed = len([t for t in tasks if t.status == "completed"])
    in_progress = len([t for t in tasks if t.status == "in_progress"])

    # In-progress tasks count as 50% complete
    return (completed + in_progress * 0.5) / total * 100
```

### Task Status Indicators
- ✅ **Completed**: Task fully implemented and tested
- 🚧 **In Progress**: Task currently being worked on
- 📋 **Planned**: Task scheduled but not started
- ⏸️ **Blocked**: Task waiting on dependency
- ❌ **Cancelled**: Task no longer needed

## ADR Management

### Creating ADRs
ADRs are created for:
- **Architecture**: Framework choices, patterns
- **Infrastructure**: Database, hosting, CI/CD
- **Security**: Authentication, authorization
- **Integration**: Third-party services
- **Performance**: Caching, optimization strategies

### ADR Lifecycle
1. **Proposed**: Decision under consideration
2. **Accepted**: Decision made and implemented
3. **Deprecated**: Decision superseded by newer ADR
4. **Rejected**: Alternative considered but not chosen

### ADR Linking
ADRs can reference each other:
```markdown
## Related ADRs
- Supersedes: ADR-002
- Related to: ADR-005
- Amended by: ADR-008
```

## Change Detection

### What Triggers Documentation Updates

1. **New Python Files**
   - Creates feature documentation
   - Updates API docs if endpoints added

2. **Model Changes**
   - Updates database schema documentation
   - Creates migration documentation

3. **Config Changes**
   - Updates configuration guide
   - Documents new environment variables

4. **Requirement Changes**
   - Updates dependency documentation
   - Notes security-sensitive dependencies

5. **Test Coverage Changes**
   - Updates quality metrics
   - Tracks test coverage percentage

## Examples

### Example 1: New Feature Branch
When creating a feature branch:
```markdown
## Branch: feature/social-features

**Created**: 2026-04-15
**Status**: In Progress

### Planned Changes
- [ ] Add like/unlike endpoints
- [ ] Add comment system
- [ ] Add activity feed
- [ ] Add notifications

### Documentation Updates Needed
- [ ] Update API-Documentation.md
- [ ] Create feature documentation
- [ ] Update database schema
- [ ] Create ADR for notification system
```

### Example 2: Task Completion
When a task is completed:
```markdown
# Current Tasks

## Sprint 3 (April 15-29, 2026)

**Overall Progress**: 45% → 60% complete

### Just Completed ✅
- [x] ~~Event management endpoints~~ (Completed 2026-04-15)
  - Added CRUD operations
  - Implemented registration system
  - Added featured events endpoint

### Now In Progress 🚧
- [ ] File upload for ride photos (60% complete)
  - ✅ Set up S3/R2 storage
  - ✅ Add upload endpoint
  - 🚧 Image processing
  - 📋 Thumbnail generation
```

## Best Practices

1. **Keep Documentation Current**
   - Run doc-sync after major changes
   - Review generated docs before committing

2. **Meaningful ADRs**
   - Document the "why", not just the "what"
   - Include alternatives considered
   - Update ADRs when decisions change

3. **Progress Tracking**
   - Update task status regularly
   - Be honest about completion percentages
   - Note blockers and dependencies

4. **Version Documentation**
   - Tag documentation with releases
   - Maintain changelog
   - Archive old versions

5. **Cross-Reference**
   - Link related documentation
   - Reference ADRs in code comments
   - Connect features to tasks

## Output Format

### Progress Report
```markdown
# GlycoGrit Backend - Progress Report
**Generated**: 2026-04-15 18:30 UTC

## Current Sprint Status
Sprint 3: 60% complete (6/10 tasks)

## Recent Completions (Last 7 Days)
- Event management API endpoints
- Docker deployment configuration
- CI/CD with GitHub Actions

## In Progress
- File upload system (60%)
- Push notifications (20%)

## Upcoming
- Social features (planned)
- Analytics dashboard (planned)

## Documentation Status
- 📝 ADRs: 5 total (4 accepted, 1 proposed)
- 📚 API Docs: 85% coverage
- 🗄️ Database Docs: 100% up-to-date
- ✅ Tests: 72% coverage
```

## Logging

All sync operations logged to:
- `.claude/doc-sync/history.json` - Sync history
- `.claude/doc-sync/changes.json` - Documentation changes
- `.claude/doc-sync/metrics.json` - Progress metrics

## Notes

- **Non-destructive**: Never removes existing documentation
- **User review**: Major changes require approval
- **Git-aware**: Respects gitignore patterns
- **Markdown-first**: All docs in markdown format
- **Living documentation**: Stays in sync with code
