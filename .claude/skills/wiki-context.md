# Wiki Context Skill

**Purpose**: Automatically load relevant wiki pages and documentation to provide context for development tasks.

## Overview

This skill fetches essential project documentation and wiki pages to help Claude understand:
- Project architecture and patterns
- Coding standards and conventions
- Security best practices
- Database schema and models
- API design guidelines
- Deployment procedures

## Context Loading Modes

### Mode 1: Full Context (Default)
Loads all essential wiki pages for comprehensive understanding.

**Includes**:
- Project README
- Architecture documentation
- Coding standards
- Design patterns
- Security best practices
- API documentation
- Database schema
- Configuration guide
- Deployment guide

**Usage**:
```bash
claude skill wiki-context --mode=full
```

### Mode 2: Code Review Context
Focused context for code review tasks.

**Includes**:
- Coding standards
- Design patterns
- Security best practices
- Python/FastAPI conventions
- Testing guidelines

**Usage**:
```bash
claude skill wiki-context --mode=code-review
```

### Mode 3: API Development Context
Context for building new API endpoints.

**Includes**:
- API documentation
- Endpoint patterns
- Authentication/authorization
- Request/response schemas
- Error handling patterns

**Usage**:
```bash
claude skill wiki-context --mode=api
```

### Mode 4: Database Context
Context for database and model work.

**Includes**:
- Database schema
- SQLAlchemy patterns
- Migration guidelines
- Relationship patterns
- Indexing strategies

**Usage**:
```bash
claude skill wiki-context --mode=database
```

### Mode 5: Security Context
Context for security-related tasks.

**Includes**:
- Security best practices
- Authentication patterns
- Authorization rules
- Input validation
- OWASP guidelines
- Secrets management

**Usage**:
```bash
claude skill wiki-context --mode=security
```

### Mode 6: Deployment Context
Context for deployment and DevOps tasks.

**Includes**:
- Deployment guide
- Docker configuration
- CI/CD workflows
- Environment configuration
- Monitoring and logging

**Usage**:
```bash
claude skill wiki-context --mode=deployment
```

### Mode 7: Planning Context
Context for planning and architecture decisions.

**Includes**:
- Product roadmap
- Current tasks
- Architecture Decision Records (ADRs)
- Technical constraints
- Feature specifications

**Usage**:
```bash
claude skill wiki-context --mode=planning
```

## Auto-Loading

The skill automatically loads relevant context based on:

1. **File Being Edited**
   - Editing `app/api/**/*.py` → Load API context
   - Editing `app/models/**/*.py` → Load database context
   - Editing `app/middleware/**/*.py` → Load security context

2. **Task Type**
   - "Create new endpoint" → API context
   - "Add database model" → Database context
   - "Review security" → Security context
   - "Deploy application" → Deployment context

3. **User Request**
   - Explicit mode specified
   - Inferred from conversation

## Wiki Pages Managed

### Essential Documentation
| File | Purpose | Load In Modes |
|------|---------|---------------|
| `README.md` | Project overview | All |
| `ARCHITECTURE.md` | System architecture | Full, Planning |
| `API-Documentation.md` | API reference | Full, API |
| `Database-Schema.md` | Database structure | Full, Database |
| `Security-Best-Practices.md` | Security guidelines | Full, Security, Code Review |
| `Design-Patterns.md` | Code patterns | Full, Code Review |
| `Configuration-Guide.md` | Environment config | Full, Deployment |
| `DEPLOYMENT.md` | Deployment guide | Full, Deployment |
| `Current-Tasks.md` | Active tasks | Planning |
| `Product-Roadmap.md` | Feature roadmap | Planning |

### Architecture Decision Records (ADRs)
| ADR | Decision | Load In Modes |
|-----|----------|---------------|
| `ADR-001-Authentication.md` | Firebase auth choice | Security, Planning |
| `ADR-002-Database-ORM.md` | SQLAlchemy 2.0 | Database, Planning |
| `ADR-003-API-Versioning.md` | API version strategy | API, Planning |
| `ADR-004-Deployment-Platform.md` | Hetzner VPS choice | Deployment, Planning |

## Context Loading Process

### 1. Detection Phase
```python
# Detect task context from file path or user request
if file_path.startswith("app/api/"):
    context_mode = "api"
elif file_path.startswith("app/models/"):
    context_mode = "database"
elif file_path.startswith("app/middleware/"):
    context_mode = "security"
else:
    context_mode = "full"
```

### 2. Loading Phase
```python
# Load relevant wiki pages
wiki_pages = load_context(context_mode)

# Parse and structure content
structured_context = {
    "architecture": parse_markdown("ARCHITECTURE.md"),
    "patterns": parse_markdown("Design-Patterns.md"),
    "security": parse_markdown("Security-Best-Practices.md"),
    # ...
}
```

### 3. Integration Phase
```python
# Provide context to Claude
context = f"""
## Project Context

### Architecture
{structured_context["architecture"]}

### Design Patterns
{structured_context["patterns"]}

### Security Guidelines
{structured_context["security"]}
"""
```

## Context Caching

To improve performance, context is cached:

### Cache Strategy
```json
{
  "cache_duration": 3600,
  "cache_key": "wiki-context-{mode}-{hash}",
  "invalidate_on": [
    "wiki_file_modified",
    "manual_refresh"
  ]
}
```

### Cache Refresh
```bash
# Manually refresh cache
claude skill wiki-context --refresh

# Auto-refresh on wiki changes
# (automatically detects wiki file modifications)
```

## Smart Context Loading

### Minimal Loading (Fast)
For quick tasks, load only essential context:
```bash
claude skill wiki-context --mode=minimal
```
**Loads**: README, current file's related docs only

### Progressive Loading
Load more context as needed:
1. Start with minimal context
2. Load additional context if task requires it
3. Cache for subsequent requests

## Integration with Other Skills

### With wiki-updater
When wiki is updated, refresh context:
```bash
# Wiki updated → Auto-refresh context
wiki-updater → wiki-context --refresh
```

### With code-review
Load code review context automatically:
```bash
# Code review triggered → Load review context
code-review → wiki-context --mode=code-review
```

### With doc-sync
Sync documentation, then update context:
```bash
# Doc sync → Update context cache
doc-sync → wiki-context --refresh
```

## Configuration

Edit `.claude/wiki-context.config.json`:

```json
{
  "enabled": true,
  "auto_load": true,
  "default_mode": "full",
  "cache": {
    "enabled": true,
    "duration": 3600,
    "max_size_mb": 10
  },
  "modes": {
    "full": {
      "files": [
        "README.md",
        "ARCHITECTURE.md",
        "API-Documentation.md",
        "Database-Schema.md",
        "Security-Best-Practices.md",
        "Design-Patterns.md",
        "Configuration-Guide.md",
        "DEPLOYMENT.md"
      ]
    },
    "code-review": {
      "files": [
        "Design-Patterns.md",
        "Security-Best-Practices.md",
        "Coding-Standards.md"
      ]
    },
    "api": {
      "files": [
        "API-Documentation.md",
        "Security-Best-Practices.md",
        "docs/adr/ADR-003-API-Versioning.md"
      ]
    },
    "database": {
      "files": [
        "Database-Schema.md",
        "docs/adr/ADR-002-Database-ORM.md"
      ]
    },
    "security": {
      "files": [
        "Security-Best-Practices.md",
        "docs/adr/ADR-001-Authentication.md"
      ]
    },
    "deployment": {
      "files": [
        "DEPLOYMENT.md",
        "Configuration-Guide.md",
        "docs/adr/ADR-004-Deployment-Platform.md"
      ]
    },
    "planning": {
      "files": [
        "Current-Tasks.md",
        "Product-Roadmap.md",
        "docs/adr/*.md"
      ]
    }
  },
  "auto_detect": {
    "enabled": true,
    "patterns": {
      "app/api/**/*.py": "api",
      "app/models/**/*.py": "database",
      "app/middleware/**/*.py": "security",
      "alembic/**/*.py": "database",
      ".github/workflows/**/*.yml": "deployment"
    }
  }
}
```

## Usage Examples

### Example 1: Starting New Feature
```bash
# Load planning context to understand current tasks
claude skill wiki-context --mode=planning

# Shows:
# - Current sprint tasks
# - Feature roadmap
# - Related ADRs
# - Technical constraints
```

### Example 2: Adding API Endpoint
```bash
# Auto-loads API context when editing app/api/v1/endpoints/rides.py
# Provides:
# - Existing endpoint patterns
# - Authentication requirements
# - Response schema conventions
# - Error handling patterns
```

### Example 3: Database Migration
```bash
# Load database context
claude skill wiki-context --mode=database

# Provides:
# - Current schema structure
# - Relationship patterns
# - Migration best practices
# - Indexing guidelines
```

### Example 4: Security Review
```bash
# Load security context for security audit
claude skill wiki-context --mode=security

# Provides:
# - Security best practices
# - Authentication patterns
# - Common vulnerabilities
# - Input validation rules
```

## Output Format

```markdown
## Context Loaded: API Development

### API Documentation
**Last Updated**: 2026-04-15

#### Endpoint Patterns
- All endpoints use async handlers
- Dependency injection for database sessions
- Response models defined with Pydantic
- Status codes: 200 (success), 201 (created), 204 (no content), 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found)

#### Authentication
- Firebase JWT validation required for protected endpoints
- Use `Depends(get_current_user)` for authenticated routes
- Token passed in `Authorization: Bearer <token>` header

#### Request/Response Patterns
- Request validation with Pydantic schemas
- Separate schemas for Create, Update, Response
- Use `response_model` parameter on route decorator

### Relevant ADRs
- **ADR-001**: Firebase Authentication (rationale: frontend integration)
- **ADR-003**: API Versioning Strategy (v1 prefix in URLs)

---
✅ Context loaded successfully. You can now proceed with API development.
```

## Benefits

✅ **Consistent Development**: Always aware of project patterns
✅ **Faster Onboarding**: New developers get context automatically
✅ **Pattern Adherence**: Easy to follow established conventions
✅ **Security Awareness**: Security guidelines always available
✅ **Decision Context**: ADRs provide rationale for architectural choices

## Notes

- **Auto-loads on startup** if enabled in config
- **Detects file context** based on path
- **Caches for performance** to reduce load times
- **Refreshes on wiki changes** to stay current
- **Integrates with other skills** for seamless workflow
