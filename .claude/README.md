# Claude Code Skills - GlycoGrit Backend

This directory contains Claude Code skills and configuration for the GlycoGrit Backend project.

## Overview

Claude Code skills are specialized capabilities that help maintain code quality, documentation, and development workflows automatically.

## Available Skills

### 1. **code-review** 📝
Automatically reviews Python/FastAPI code for adherence to project standards and best practices.

**Usage**:
```bash
claude skill code-review
```

**Checks**:
- File organization and naming
- FastAPI best practices
- Python type hints
- SQLAlchemy 2.0 patterns
- Pydantic schema design
- Authentication & authorization
- Error handling
- Security best practices
- Code organization
- Performance considerations

**Configuration**: `.claude/code-review.config.json`

---

### 2. **wiki-updater** 📚
Detects significant code changes and proposes updates to project wiki/documentation.

**Usage**:
```bash
claude skill wiki-updater
claude skill wiki-updater --dry-run  # Preview changes
```

**Triggers On**:
- New API endpoints
- Database model changes
- Security implementations
- Configuration changes
- Design pattern introductions

**Wiki Pages Updated**:
- `API-Documentation.md`
- `Database-Schema.md`
- `Security-Best-Practices.md`
- `Design-Patterns.md`
- `Configuration-Guide.md`

**Configuration**: `.claude/wiki-updater.config.json`

**Logs**: `.claude/wiki-updates/`

---

### 3. **doc-sync** 🔄
Synchronizes documentation with code changes, maintains task lists, and creates ADRs.

**Usage**:
```bash
claude skill doc-sync
claude skill doc-sync --type=tasks      # Sync task lists only
claude skill doc-sync --type=adr        # Create ADR
claude skill doc-sync --type=features   # Update feature docs
```

**Features**:
- Task completion tracking with percentages
- Architecture Decision Records (ADRs)
- Feature documentation auto-generation
- Changelog maintenance
- Progress reports

**Manages**:
- `Current-Tasks.md`
- `Product-Roadmap.md`
- `docs/adr/*.md`
- `CHANGELOG.md`
- `docs/features/*.md`

**Configuration**: `.claude/doc-sync.config.json`

**Logs**: `.claude/doc-sync/`

---

### 4. **wiki-context** 🧠
Loads relevant project documentation to provide context for development tasks.

**Usage**:
```bash
claude skill wiki-context                    # Full context
claude skill wiki-context --mode=api         # API development context
claude skill wiki-context --mode=database    # Database context
claude skill wiki-context --mode=security    # Security context
claude skill wiki-context --mode=deployment  # Deployment context
claude skill wiki-context --mode=planning    # Planning context
claude skill wiki-context --refresh          # Refresh cache
```

**Context Modes**:
- **full**: Complete project context
- **code-review**: Code review standards
- **api**: API development patterns
- **database**: Database and models
- **security**: Security guidelines
- **deployment**: Deployment procedures
- **planning**: Roadmap and tasks

**Auto-Detection**: Automatically loads relevant context based on file being edited.

**Configuration**: `.claude/wiki-context.config.json`

---

## Configuration Files

### `managed-settings.json`
Main Claude Code configuration with:
- Allowed/denied bash commands
- File access restrictions
- Security policies
- Project context

### `*.config.json`
Individual skill configurations:
- `code-review.config.json` - Review rules and thresholds
- `wiki-updater.config.json` - Detection patterns and wiki mappings
- `doc-sync.config.json` - Documentation sync settings
- `wiki-context.config.json` - Context loading modes

## Directory Structure

```
.claude/
├── README.md                       # This file
├── managed-settings.json           # Main Claude Code config
├── skills/
│   ├── code-review.md             # Code review skill
│   ├── wiki-updater.md            # Wiki updater skill
│   ├── doc-sync.md                # Documentation sync skill
│   └── wiki-context.md            # Context loader skill
├── code-review.config.json        # Code review configuration
├── wiki-updater.config.json       # Wiki updater configuration
├── doc-sync.config.json           # Doc sync configuration
├── wiki-context.config.json       # Context loader configuration
├── wiki-updates/                  # Wiki update logs
│   ├── history.json
│   ├── pending.json
│   └── applied.json
├── doc-sync/                      # Doc sync logs
│   ├── history.json
│   ├── changes.json
│   └── metrics.json
├── code-review/                   # Code review logs
│   ├── history.json
│   └── reports/
└── cache/                         # Context cache
```

## Security Features

### File Access Restrictions
Claude Code **cannot read** these files:
- `.env`, `.env.local`, `.env.*.local`
- `*.pem`, `*.key`, `*.crt` (SSL certificates)
- `id_rsa*`, `id_dsa*`, etc. (SSH keys)
- `firebase-credentials.json`
- `**/secrets/**`
- Cloud credentials (`.aws/`, `.gcloud/`, etc.)
- Password files, tokens, etc.

### Command Restrictions
Claude Code **cannot execute**:
- Destructive commands (`rm -rf`, `sudo`, `chmod 777`)
- Network commands (`curl`, `wget`, `ssh`, `scp`)
- Dangerous git commands (`push --force`, `config --global`)
- Package installation (`pip install`, `npm install`)
- Secret management (`gh secret set`, `doppler secrets set`)

## Workflows

### Development Workflow

1. **Start Development**
   ```bash
   # Context automatically loaded based on file
   # Edit app/api/v1/endpoints/rides.py
   # → API context loaded
   ```

2. **Write Code**
   ```bash
   # Code review runs automatically on save
   # Provides real-time feedback
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "Add ride join endpoint"

   # wiki-updater detects changes
   # Proposes wiki updates
   ```

4. **Update Documentation**
   ```bash
   # Accept proposed wiki updates
   # doc-sync updates task lists
   # Progress tracked automatically
   ```

### Code Review Workflow

```bash
# Automatic review on file save
# ✅ Passed checks shown
# ⚠️  Warnings highlighted
# ❌ Errors must be fixed

# Manual trigger
claude skill code-review
```

### Documentation Workflow

```bash
# 1. Make significant code change
# 2. wiki-updater detects pattern
# 3. Review proposed update
# 4. Approve and apply
# 5. doc-sync tracks completion
```

### Planning Workflow

```bash
# Load planning context
claude skill wiki-context --mode=planning

# Review Current-Tasks.md
# See progress percentages
# Check roadmap alignment

# Create ADR for major decision
claude skill doc-sync --create-adr "Use PostgreSQL for caching"
```

## Integration with Doppler

Secrets management is handled by Doppler:

**See**: [`DOPPLER_QUICKSTART.md`](../DOPPLER_QUICKSTART.md)

**Quick Start**:
```bash
# Install Doppler CLI
brew install dopplerhq/cli/doppler

# Login and setup
doppler login
doppler setup

# Run app with secrets
doppler run -- uvicorn app.main:app --reload
```

## Best Practices

### 1. Use Skills Proactively
- Let `wiki-context` load context automatically
- Trust `code-review` feedback
- Apply `wiki-updater` proposals regularly
- Keep task lists updated with `doc-sync`

### 2. Review Before Applying
- Always review wiki update proposals
- Check code review recommendations
- Verify ADRs before creation
- Approve documentation changes

### 3. Keep Configuration Updated
- Adjust thresholds as project matures
- Add new detection patterns
- Update wiki page mappings
- Configure auto-load patterns

### 4. Maintain Documentation
- Update wiki pages regularly
- Create ADRs for major decisions
- Track task completion
- Keep roadmap current

### 5. Security First
- Never commit secrets
- Use Doppler for all sensitive config
- Follow security best practices
- Review security checks

## Troubleshooting

### Skill Not Working
```bash
# Check skill exists
ls .claude/skills/

# Verify configuration
cat .claude/wiki-updater.config.json

# Check Claude Code is running
claude --version
```

### Context Not Loading
```bash
# Refresh cache
claude skill wiki-context --refresh

# Check configuration
cat .claude/wiki-context.config.json

# Verify wiki files exist
ls API-Documentation.md Database-Schema.md
```

### Wiki Updates Not Detected
```bash
# Check watch patterns
cat .claude/wiki-updater.config.json | grep watch_patterns

# Verify files match patterns
# e.g., app/api/**/*.py

# Check logs
cat .claude/wiki-updates/history.json
```

## Extending Skills

### Add New Detection Pattern

Edit `.claude/wiki-updater.config.json`:
```json
{
  "detection_rules": {
    "new_pattern": {
      "pattern": "your_regex_here",
      "files": ["app/**/*.py"]
    }
  }
}
```

### Add New Wiki Page

Edit `.claude/wiki-updater.config.json`:
```json
{
  "wiki_pages": {
    "new_page": {
      "file": "New-Documentation.md",
      "triggers": ["new_pattern"]
    }
  }
}
```

### Add New Context Mode

Edit `.claude/wiki-context.config.json`:
```json
{
  "modes": {
    "custom": {
      "description": "Custom context mode",
      "files": ["Custom-Doc.md"]
    }
  }
}
```

## Resources

- **Claude Code Docs**: https://docs.anthropic.com/claude/docs/claude-code
- **Skills Guide**: See individual skill `.md` files
- **Configuration**: See `*.config.json` files
- **Doppler Docs**: https://docs.doppler.com/

## Support

For issues with:
- **Claude Code**: https://github.com/anthropics/claude-code/issues
- **Project-specific**: Create issue in this repository
- **Doppler**: https://community.doppler.com/

---

**Last Updated**: 2026-04-15
**Version**: 1.0.0
**Maintained By**: GlycoGrit Team
