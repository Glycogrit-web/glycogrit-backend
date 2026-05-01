---
name: doc-sync
description: "Automatically detects code changes and updates relevant documentation (wiki pages, README, task lists) with progress tracking, completion percentages, decision records, and new feature documentation. Triggers after code modifications to maintain documentation-code synchronization."
---

# Documentation Sync Skill

This skill automatically keeps documentation synchronized with code changes, tracking progress, decisions, and architectural evolution. It's inspired by NOVA's practice of maintaining living documentation.

---

## When This Skill Activates

This skill automatically runs after:
- ✅ Completing a feature or task
- ✅ Modifying existing functionality
- ✅ Adding new architectural patterns
- ✅ Making significant design decisions
- ✅ Implementing new integrations
- ✅ Refactoring code structure
- ✅ Completing sprint milestones

---

## What Gets Updated

### 1. Task Lists & Progress Tracking

**Automatically updates:**
- `Current-Tasks.md` - Mark tasks as completed, update progress
- `Product-Roadmap.md` - Update phase completion percentages
- Project board - Sync GitHub Issues/Projects

**Update format:**
```markdown
## Current Sprint Progress: 65% Complete

### Completed This Sprint ✅
- [x] Set up Doppler integration (100%) - 2 hours
  - Expected: Centralized secret management
  - Actual: Successfully integrated, all tests pass
  - Decision: Using free tier, will upgrade at 5+ projects

- [x] Create documentation structure (100%) - 3 hours
  - Expected: Clear wiki organization
  - Actual: Exceeded expectations - added auto-sync skill
  - Pros: Single source of truth, easy navigation
  - Cons: Initial learning curve for team

### In Progress 🚧
- [ ] Landing page redesign (40%) - 8/20 hours
  - Completed: Hero section, navigation
  - Remaining: Features section, testimonials, footer
  - Blocker: Waiting for final logo from design team

### Not Started 📋
- [ ] User authentication (0%) - 15 hours estimated
```

### 2. Architectural Decision Records (ADRs)

**When a significant technical decision is made, automatically creates:**

`Architecture-Decision-Records/ADR-XXX-title.md`

```markdown
# ADR-003: Use Doppler for Secret Management

**Status:** Accepted
**Date:** April 14, 2026
**Deciders:** Development Team
**Related:** [Secret Management Guide](../Secret-Management.md)

## Context

We needed a centralized secret management solution for multiple environments (dev/staging/prod) as the project scales. Manual .env file management was becoming error-prone.

## Decision

We will use Doppler (free tier) as our centralized secret management system, following NOVA's vault-style approach.

## Alternatives Considered

1. **Vercel Environment Variables** (Current)
   - Pros: Already using, free, simple
   - Cons: Only works for frontend, manual sync, no audit logs

2. **AWS Secrets Manager**
   - Pros: Enterprise-grade, automatic rotation
   - Cons: $0.40/secret/month, requires AWS infrastructure, complex setup

3. **HashiCorp Vault** (NOVA's choice)
   - Pros: Enterprise-grade, full control
   - Cons: Requires infrastructure, complex maintenance, overkill for our scale

## Rationale

- ✅ **Free tier** covers our needs (unlimited secrets, 5 users, 3 projects)
- ✅ **Auto-sync** to Vercel, Railway, GitHub Actions
- ✅ **Audit logs** for compliance
- ✅ **Environment profiles** (like NOVA's approach)
- ✅ **CLI integration** for local development
- ✅ **Team collaboration** with role-based access

## Consequences

### Positive
- Single source of truth for all secrets
- Automatic sync reduces deployment errors
- Audit logs improve security compliance
- Easy onboarding for new developers
- No cost until we scale significantly

### Negative
- New dependency (vendor lock-in risk)
- Team needs to learn Doppler CLI
- Requires internet connection for `doppler run`
- Free tier limits (3 projects) - will need upgrade eventually

### Neutral
- Migration effort: ~2 hours one-time setup
- Documentation overhead: Created comprehensive guide

## Implementation

- [Doppler Setup Guide](../Doppler-Setup-Guide.md)
- [Secret Management Strategy](../Secret-Management.md)
- Configuration: `doppler.yaml`
- Scripts: `package.json` (`dev:doppler`, `build:doppler`)

## Review Date

- **Next Review:** July 2026 (when backend is added)
- **Triggers for Reevaluation:**
  - Exceed 3 projects (need upgrade)
  - Team grows beyond 5 people
  - Compliance requirements change
  - Migration to AWS infrastructure

## References

- NOVA project secret management patterns
- Doppler documentation: https://docs.doppler.com
- Issue: #123 (Secret management strategy)
```

### 3. Feature Documentation

**When a new feature is implemented, automatically creates wiki page:**

`Feature-Name.md`

```markdown
# Feature: Doppler Secret Management Integration

**Status:** ✅ Implemented
**Version:** 1.0.0
**Date Completed:** April 14, 2026
**Developer:** Team
**Related ADR:** [ADR-003](../Architecture-Decision-Records/ADR-003.md)

---

## Overview

Centralized secret management using Doppler, replacing manual .env file management.

## What Was Built

### 1. Configuration Files
- `doppler.yaml` - Project configuration
- `.github/workflows/deploy-with-doppler.yml` - CI/CD integration
- Updated `package.json` with Doppler scripts

### 2. Documentation
- [Doppler Setup Guide](./Doppler-Setup-Guide.md) - 15-part tutorial
- [DOPPLER_QUICKSTART.md](../../glycogrit-frontend/DOPPLER_QUICKSTART.md)
- [Secret Management](./Secret-Management.md) - Strategic overview

### 3. Integrations
- ✅ Vercel automatic sync
- ✅ GitHub Actions integration
- ✅ CLI for local development
- 🔄 Railway (ready for backend)

## How It Works

```
┌──────────────┐
│   Doppler    │ ← Single source of truth
└──────┬───────┘
       │
   ┌───┴────┬────────┬─────────┐
   ▼        ▼        ▼         ▼
Vercel  Railway  GitHub   Local Dev
Frontend Backend  Actions  (CLI)
```

## Usage

```bash
# Run development with secrets
npm run dev:doppler

# View secrets
doppler secrets

# Switch environments
doppler setup --config prd
```

## Configuration

### Environments

| Config | Environment | Secrets Count | Sync Target |
|--------|-------------|---------------|-------------|
| `dev` | Local development | 12 | Local CLI |
| `stg` | Staging | 15 | Vercel Preview |
| `prd` | Production | 18 | Vercel Production |

### Secret Categories

1. **Application** (5 secrets)
   - VITE_APP_NAME, VITE_ENVIRONMENT, etc.

2. **API Configuration** (4 secrets)
   - VITE_API_BASE_URL, VITE_API_TIMEOUT, etc.

3. **Third-party** (3 secrets)
   - VITE_STRIPE_PUBLISHABLE_KEY, etc.

4. **Feature Flags** (6 secrets)
   - VITE_ENABLE_DEBUG_MODE, etc.

## Testing

### Manual Testing
- ✅ Local development with `npm run dev:doppler`
- ✅ Secrets correctly injected into app
- ✅ Environment switching works
- ✅ Vercel sync verified

### Integration Testing
- ✅ CI/CD pipeline builds with Doppler
- ✅ Preview deployments get staging secrets
- ✅ Production deployments get prod secrets

## Performance Impact

- **Build time:** No significant change (~1-2 seconds for secret fetch)
- **Dev server startup:** +0.5 seconds (Doppler CLI overhead)
- **Bundle size:** No impact (secrets injected at build time)

## Security Improvements

- ✅ No secrets in git history
- ✅ Audit logs for all changes
- ✅ Role-based access control
- ✅ Encrypted storage
- ✅ Automatic sync eliminates manual errors

## Migration Notes

### What Changed
- **Before:** Manual .env.local files on each machine
- **After:** Central Doppler configuration

### Breaking Changes
- None (backward compatible - .env.local still works)

### Rollback Plan
1. Export secrets: `doppler secrets download > .env.local`
2. Revert code changes
3. Use regular `npm run dev`

## Known Issues

None

## Future Enhancements

- [ ] Add secret rotation reminders
- [ ] Integrate with backend when ready
- [ ] Add more audit log automation
- [ ] Create secret usage analytics

## Dependencies

```json
{
  "runtime": [],
  "development": ["dopplerhq/cli"],
  "external": ["Doppler service"]
}
```

## Cost

- **Current:** $0/month (free tier)
- **Projected:** $0-9/month (when we exceed 3 projects)

## Team Training

- **Training docs:** [Doppler Setup Guide](./Doppler-Setup-Guide.md)
- **Time to onboard:** 15 minutes
- **Team members trained:** 2/2 (100%)

## Metrics & Success Criteria

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Setup time | < 30 min | 25 min | ✅ |
| Secret sync reliability | > 99% | 100% | ✅ |
| Team adoption | 100% | 100% | ✅ |
| Build failures due to secrets | 0 | 0 | ✅ |

## Lessons Learned

### What Went Well ✅
- Doppler free tier perfect for our scale
- Documentation-first approach paid off
- NOVA-inspired patterns easy to implement
- Auto-sync eliminates manual errors

### What Could Be Improved ⚠️
- OAuth scope issue with GitHub workflows (workaround: manual add)
- Initial learning curve for CLI commands
- Requires internet for `doppler run`

### What We'd Do Differently 🔄
- Set up Doppler before writing any code
- Create video tutorial for team onboarding
- Add more secret usage examples

## Related Documentation

- [ADR-003: Doppler Decision](../Architecture-Decision-Records/ADR-003.md)
- [Secret Management Guide](./Secret-Management.md)
- [Deployment Guide](./Deployment-Guide.md)

---

**Maintained by:** Development Team
**Last Updated:** April 14, 2026
**Next Review:** July 2026 (when backend added)
