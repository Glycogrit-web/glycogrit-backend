---
name: wiki-context
description: "Automatically fetches essential wiki pages (Coding Standards, Design Patterns, Security, Project Management, Deployment) from GitHub Wiki to provide context for code analysis, development, and project planning. Triggers when relevant architectural, coding standard, deployment, or planning questions arise."
---

# Wiki Context Skill

This skill automatically fetches important wiki documentation from GitHub Wiki to provide Claude with context about the project's coding standards, architecture patterns, security practices, deployment infrastructure, and project management.

## When This Skill Activates

This skill is automatically invoked when:
- Analyzing code for standards compliance
- Making architectural decisions
- Reviewing security implementations
- Answering questions about project conventions
- Creating new components or patterns
- Discussing deployment or infrastructure
- Planning features or reviewing roadmap
- Managing tasks or sprint planning

## Wiki Pages Fetched

### Core Documentation (Development)
1. **Coding Standards** - TypeScript patterns, naming conventions, file organization
2. **Design Patterns** - Singleton, Configuration Classes, Custom Hooks, Error Handling
3. **Security Best Practices** - XSS, CSRF, authentication, secrets management

### Context-Specific Development
4. **Component Guidelines** - When working with React components
5. **State Management** - When implementing state logic
6. **Project Structure** - When organizing files or modules

### Project Management & Planning
7. **Project Management** - GitHub Projects workflow, task tracking, sprint ceremonies
8. **Current Tasks** - Active sprint tasks, next steps, immediate action items
9. **Product Roadmap** - Development phases, milestones, long-term vision

### Deployment & Operations
10. **Deployment Guide** - Vercel setup, Railway backend, multi-service architecture, DNS, security

## How It Works

```bash
# Usage: wiki-context.sh [context-mode]
# Available modes:
#   full                - All core development pages (default)
#   code-review         - Coding Standards + Security
#   component           - Component Guidelines + Design Patterns
#   architecture        - Design Patterns + Project Structure
#   security            - Security Best Practices (full)
#   project-management  - Project Management + Current Tasks
#   deployment          - Deployment Guide (full)
#   planning            - Product Roadmap + Current Tasks

# Examples:
./wiki-context.sh full                # Core development context
./wiki-context.sh deployment          # Infrastructure questions
./wiki-context.sh project-management  # Task tracking, workflow
./wiki-context.sh planning            # Roadmap and sprint planning
```

## Output Format

The skill provides:

```markdown
# Wiki Context for Development

## Coding Standards Summary
- TypeScript strict mode required
- PascalCase for components, camelCase for functions
- Functional components with hooks
- Props interfaces with Props suffix

## Design Patterns in Use
- Singleton: API clients
- Configuration Classes: Static readonly properties
- Custom Hooks: Reusable business logic
- Error Handling: Custom error classes with type discrimination

## Security Requirements
- No hardcoded secrets
- Input validation and sanitization
- XSS prevention with React escaping
- CSRF protection with SameSite cookies

[Full details available in wiki pages]
```

## Environment Variables

- `GITHUB_TOKEN` or `GH_TOKEN` - For accessing GitHub API (optional for public wikis)
- `GH_HOST` - GitHub hostname (default: github.com)

## Error Handling

The skill gracefully handles:
- Wiki page not found → Uses cached version or skips
- API rate limit → Provides summary without full content
- Network errors → Continues with basic context

## Integration with Development

When this skill runs successfully, it provides:
- **Context about coding standards** for code reviews
- **Architecture patterns** to follow when implementing features
- **Security guidelines** to check against
- **Component patterns** for consistent development

### Smart Context Loading

The skill is intelligent about what to load based on context:

| Task | Wiki Pages Loaded | Context Mode |
|------|-------------------|--------------|
| Code review | Coding Standards, Security | `code-review` |
| New component | Coding Standards, Component Guidelines, Design Patterns | `component` |
| API integration | Design Patterns (Singleton), Security | `security` |
| State management | State Management, Design Patterns (Hooks) | `component` |
| Architecture decision | Design Patterns, Project Structure | `architecture` |
| Deployment questions | Deployment Guide | `deployment` |
| Task planning | Current Tasks, Project Management | `project-management` |
| Roadmap review | Product Roadmap, Current Tasks | `planning` |
| General development | All core development pages | `full` |

## Script Reference

The wiki fetching logic is implemented using GitHub CLI:

```bash
#!/bin/bash

# Fetch essential wiki pages
fetch_wiki() {
  local page=$1
  gh api "repos/glycogrit-team/glycogrit-frontend/wiki/${page}" \
    -H "Accept: application/vnd.github.v3.raw" 2>/dev/null || echo "## ${page} (cached)"
}

# Core pages
fetch_wiki "01-Coding-Standards"
fetch_wiki "05-Design-Patterns"
fetch_wiki "04-Security-Best-Practices"
```

## Auto-Update Detection

This skill also monitors for changes that should trigger wiki updates:

| Change Type | Wiki Page to Update | Trigger |
|-------------|---------------------|---------|
| New design pattern | Design Patterns | Class/pattern added to `/lib/` |
| Coding convention change | Coding Standards | ESLint/Prettier config modified |
| Security implementation | Security Best Practices | Auth/security code modified |
| Component pattern | Component Guidelines | New component pattern in `/components/` |

When such changes are detected, the skill triggers the `wiki-updater` skill.

## Benefits

✅ **Always up-to-date context** - Fetches latest wiki content
✅ **Lightweight** - Only fetches what's needed
✅ **Smart caching** - Reduces API calls
✅ **Automatic updates** - Triggers wiki updates when code changes
✅ **Consistent standards** - Ensures compliance with project conventions

## Usage in Code Reviews

Example workflow:
1. Developer submits PR with new component
2. `wiki-context` skill fetches Component Guidelines + Coding Standards
3. Claude reviews code against wiki standards
4. Provides feedback based on documented patterns
5. If new pattern introduced, suggests updating wiki

## Related Skills

- **code-review** - Uses wiki context for code analysis
- **arch-check** - Validates against Design Patterns wiki
- **name-check** - Enforces naming from Coding Standards wiki
- **wiki-updater** - Updates wiki when patterns change

---

**Last Updated**: April 14, 2024
**Wiki Location**: https://github.com/glycogrit-team/glycogrit-frontend/wiki
