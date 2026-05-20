# GLYCOGRIT BACKEND - COMPLETE DDD MIGRATION PLAN

## Executive Summary

This plan outlines a comprehensive Domain-Driven Design (DDD) migration for the glycogrit-backend, transforming the codebase from a mixed architecture into a fully modular, domain-centric structure. The migration will consolidate all business logic into `app/modules/`, refactor fitness trackers to use the OAuth framework, organize documentation hierarchically, and clean up technical debt.

**Current State:**
- 4 modules partially migrated (Events, Payments, Registrations, Shipping) - ~40% complete
- OAuth framework exists but not fully adopted
- Mixed structure: legacy `app/api/`, `app/services/`, and new `app/modules/`
- 40+ documentation files scattered in root
- 14 utility scripts in root directory
- 17,000+ lines across API and services layers

**Target State:**
- 100% DDD modular architecture in `app/modules/`
- All fitness trackers using unified OAuth framework in `app/integrations/`
- Structured documentation in `docs/` hierarchy
- Organized scripts in `scripts/` subdirectories
- Thin API layer delegating to domain services
- Zero duplication, high cohesion, low coupling

---

## Timeline Summary

**Total Estimated Duration: 5-6 weeks**

| Phase | Duration | Description |
|-------|----------|-------------|
| Pre-Migration | 1 day | Setup, planning, team alignment |
| Wave 1: Foundation | 2 weeks | Users & Activities modules |
| Wave 2: Fitness Integration | 2 weeks | Fitness Trackers + OAuth framework |
| Wave 3: Feature Modules | 2 weeks | Certificates, Rewards, Challenges |
| Wave 4: Support Modules | 1 week | Statistics, Gallery |
| Integration Consolidation | 1 week | Move integrations layer |
| Root Organization | 3 days | Scripts & documentation |
| Cleanup | 2 days | Delete old files |
| Testing & Validation | 3 days | Full test suite |
| Deployment | 2 days | Staging → Production |

---

## Phase 1: Domain Analysis & Structure Design

### 1.1 Identified Domains

#### Already Migrated (Keep & Enhance)
1. **Events** - Event lifecycle, capacity, registration periods
2. **Payments** - Payment processing, refunds, verification
3. **Registrations** - Event registrations, tiers, bib numbers
4. **Shipping** - Shiprocket integration, fulfillment, tracking

#### To Be Migrated (Priority Order)
5. **Users** - User accounts, profiles, authentication, roles
6. **Activities** - Activity submissions, tracking, file parsing, progress
7. **Fitness Trackers** - Connections, OAuth, sync management
8. **Certificates** - Certificate generation, download tracking, sharing
9. **Rewards** - Reward eligibility, fulfillment, user rewards
10. **Challenges** - Challenge evaluation, scheduling, progress tracking
11. **Statistics** - Site statistics, analytics, aggregations
12. **Gallery** - Image storage, Instagram integration, media management

### 1.2 Target Module Structure

```
app/modules/
├── users/                     # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py        # UserEntity (business rules)
│   │   ├── value_objects.py   # Email, PhoneNumber, UserRole
│   │   └── user.py            # User model (SQLAlchemy)
│   ├── services/
│   │   ├── user_service.py    # User CRUD, profile management
│   │   ├── auth_service.py    # Authentication, JWT, OAuth
│   │   ├── commands.py        # RegisterUser, UpdateProfile
│   │   └── queries.py         # GetUserById, SearchUsers
│   ├── repositories/
│   │   └── user_repository.py
│   ├── schemas/
│   │   ├── user.py            # User response schemas
│   │   └── auth.py            # Login, Register, Token schemas
│   └── api/
│       ├── auth.py            # Auth endpoints
│       └── users.py           # User endpoints
│
├── activities/                # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py        # ActivityEntity, ProgressEntity
│   │   ├── value_objects.py   # Distance, Duration, ActivityType
│   │   ├── activity_log.py    # UserActivityLog model
│   │   └── progress.py        # ActivityProgress model
│   ├── services/
│   │   ├── activity_service.py
│   │   ├── progress_service.py
│   │   ├── file_parser_service.py
│   │   ├── sync_service.py
│   │   ├── validation_service.py
│   │   ├── commands.py
│   │   └── queries.py
│   ├── repositories/
│   │   ├── activity_repository.py
│   │   └── progress_repository.py
│   ├── schemas/
│   │   ├── activity.py
│   │   └── progress.py
│   └── api/
│       ├── activities.py
│       └── progress.py
│
├── fitness_trackers/          # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py        # ConnectionEntity
│   │   ├── value_objects.py   # ProviderType, SyncStatus
│   │   ├── connection.py      # FitnessTrackerConnection
│   │   ├── strava.py          # StravaConnection
│   │   ├── fitbit.py          # FitbitConnection
│   │   ├── garmin.py          # GarminConnection
│   │   └── wahoo.py           # WahooConnection
│   ├── services/
│   │   ├── connection_service.py
│   │   ├── sync_coordinator.py
│   │   ├── commands.py
│   │   └── queries.py
│   ├── repositories/
│   │   └── connection_repository.py
│   ├── schemas/
│   │   └── connection.py
│   └── api/
│       └── fitness_trackers.py  # Unified API
│
├── certificates/              # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py
│   │   └── value_objects.py
│   ├── services/
│   │   ├── certificate_service.py
│   │   ├── generation_service.py
│   │   ├── sharing_service.py
│   │   ├── commands.py
│   │   └── queries.py
│   ├── repositories/
│   │   └── download_repository.py
│   ├── schemas/
│   │   └── certificate.py
│   └── api/
│       └── certificates.py
│
├── rewards/                   # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   └── reward.py
│   ├── services/
│   │   ├── reward_service.py
│   │   ├── fulfillment_service.py
│   │   ├── commands.py
│   │   └── queries.py
│   ├── repositories/
│   │   └── reward_repository.py
│   ├── schemas/
│   │   └── reward.py
│   └── api/
│       └── rewards.py
│
├── challenges/                # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   └── challenge.py
│   ├── services/
│   │   ├── challenge_service.py
│   │   ├── evaluation_service.py
│   │   ├── scheduler_service.py
│   │   ├── commands.py
│   │   └── queries.py
│   ├── repositories/
│   │   └── challenge_repository.py
│   ├── schemas/
│   │   └── challenge.py
│   └── api/
│       └── challenges.py
│
├── statistics/                # 🆕 NEW MODULE
│   ├── domain/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   └── statistics.py
│   ├── services/
│   │   ├── statistics_service.py
│   │   ├── aggregation_service.py
│   │   ├── commands.py
│   │   └── queries.py
│   ├── repositories/
│   │   └── statistics_repository.py
│   ├── schemas/
│   │   └── statistics.py
│   └── api/
│       └── statistics.py
│
└── gallery/                   # 🆕 NEW MODULE
    ├── domain/
    │   ├── entities.py
    │   ├── value_objects.py
    │   └── image.py
    ├── services/
    │   ├── gallery_service.py
    │   ├── storage_service.py
    │   ├── instagram_service.py
    │   ├── commands.py
    │   └── queries.py
    ├── repositories/
    │   └── gallery_repository.py
    ├── schemas/
    │   └── gallery.py
    └── api/
        └── gallery.py
```

### 1.3 Integration Layer Structure

```
app/integrations/
├── oauth/                     # ✅ ENHANCE EXISTING
│   ├── base.py
│   ├── factory.py
│   ├── exceptions.py
│   └── providers/
│       ├── strava.py          # ✅ Exists
│       ├── fitbit.py          # ✅ Exists
│       ├── garmin.py          # ✅ Exists
│       ├── wahoo.py           # 🆕 ADD
│       └── google_fit.py      # 🆕 ADD
│
├── payment_gateways/          # 🆕 MOVE FROM services/
│   ├── base.py
│   ├── factory.py
│   └── providers/
│       ├── razorpay.py
│       └── stripe.py          # (Future)
│
└── external_services/         # 🆕 NEW
    ├── instagram.py           # Instagram API client
    ├── cloudflare_r2.py       # R2 storage client
    └── email.py               # (Future)
```

---

## Phase 2: Migration Order & Dependencies

### Wave 1: Foundation (Week 1-2)
**Priority:** Establish base infrastructure

1. **Users Module** (3 days)
   - Extract from app/api/auth.py (687 lines)
   - Extract from app/services/user_service.py
   - Dependencies: None (foundational)

2. **Activities Module** (4 days)
   - Extract from app/api/activities.py, activity_progress.py (539 lines total)
   - Extract from multiple services (activity_service, file_parser, validation)
   - Dependencies: Users, Events

### Wave 2: Fitness Integration (Week 2-3)
**Priority:** Consolidate all fitness tracker logic

3. **Fitness Trackers Module** (7 days)
   - Extract from 6 API files (3,511 lines total - MASSIVE)
   - Refactor to use app/integrations/oauth/ framework
   - Dependencies: Users, Activities
   - **Impact:** Eliminates 2,600+ lines of duplicate OAuth code

### Wave 3: Feature Modules (Week 3-4)
**Priority:** Complete user-facing features

4. **Certificates Module** (3 days)
   - Extract from app/api/certificates.py (736 lines)
   - Dependencies: Users, Events, Registrations

5. **Rewards Module** (4 days)
   - Extract from app/api/rewards.py (1,123 lines - 2ND LARGEST)
   - Dependencies: Users, Events, Registrations, Shipping

6. **Challenges Module** (3 days)
   - Extract from app/api/challenges.py (353 lines)
   - Dependencies: Users, Events, Activities

### Wave 4: Support Modules (Week 4-5)
**Priority:** Complete infrastructure

7. **Statistics Module** (2 days)
   - Dependencies: All modules (aggregates data)

8. **Gallery Module** (2 days)
   - Dependencies: Users

---

## Phase 3: Integration Layer Consolidation

### 3.1 OAuth Framework Migration

**Current State:**
- Framework exists with Strava, Fitbit, Garmin
- Wahoo, Google Fit have legacy implementations

**Migration Steps:**

1. Create `app/integrations/oauth/providers/wahoo.py`
2. Create `app/integrations/oauth/providers/google_fit.py`
3. Update OAuthProviderFactory to register new providers
4. Migrate fitness_trackers API to use framework
5. Delete old API files (strava.py, fitbit.py, garmin.py, wahoo.py, google_fit.py)

**Files to Delete:**
- ❌ app/api/strava.py (507 lines)
- ❌ app/api/fitbit.py (596 lines)
- ❌ app/api/garmin.py (325 lines)
- ❌ app/api/wahoo.py (549 lines)
- ❌ app/api/google_fit.py (590 lines)
- ❌ app/api/fitness_trackers.py (944 lines)

**Result:** 3,511 lines → ~300 lines unified API

### 3.2 Payment Gateway Integration

Move app/services/payment_gateway/ → app/integrations/payment_gateways/

### 3.3 External Services

- Instagram service → app/integrations/external_services/
- Storage service → app/integrations/external_services/

---

## Phase 4: Root Organization

### 4.1 Scripts Organization

```
scripts/
├── database/
│   ├── manage_db.py
│   └── run_migrations.py
│
├── registrations/
│   ├── check_all_registrations.py
│   ├── check_registration.py
│   ├── cleanup_duplicates.py
│   ├── fix_status.py
│   └── merge_duplicates.py
│
├── infrastructure/
│   ├── configure_r2_cors.py
│   └── configure_shiprocket.py
│
├── social/
│   ├── get_instagram_account_id.py
│   ├── setup_instagram_token.sh
│   └── convert_to_long_lived_token.py
│
├── statistics/
│   └── refresh_statistics.py
│
├── testing/
│   ├── run_tests.sh
│   └── test_certificate_manual.py
│
└── maintenance/
    └── quick_update_password.py
```

### 4.2 Documentation Organization

```
docs/
├── README.md                          # Master index
│
├── architecture/
│   ├── MODULAR_ARCHITECTURE.md
│   ├── ARCHITECTURE_SUMMARY.md
│   ├── ARCHITECTURE_IMPROVEMENTS.md
│   └── REFACTORING_GUIDE.md
│
├── api/
│   ├── API_ENDPOINTS.md
│   ├── API_MIGRATION_EXAMPLES.md
│   └── USAGE_EXAMPLES.md
│
├── database/
│   ├── DATABASE_SCHEMA_EXPLAINED.md
│   ├── DATABASE_SETUP.md
│   └── SCHEMA_CHANGES.md
│
├── deployment/
│   ├── DOCKER.md
│   ├── RAILWAY_SETUP.md
│   ├── DEPLOYMENT_STATUS.md
│   └── PRODUCTION_READINESS_CHECKLIST.md
│
├── features/
│   ├── certificates/
│   │   ├── CERTIFICATE_README.md
│   │   ├── CERTIFICATE_FLOW_COMPLETE.md
│   │   └── CERTIFICATE_TESTING_GUIDE.md
│   ├── payments/
│   │   └── PAYMENT_INTEGRATION.md
│   └── security/
│       └── SECURITY_IMPROVEMENTS.md
│
├── guides/
│   ├── SETUP_CHECKLIST.md
│   ├── MIGRATION_GUIDE.md
│   └── NEXT_STEPS.md
│
├── testing/
│   ├── TESTING_GUIDELINES.md
│   └── TEST_FIXES_SUMMARY.md
│
└── project_history/
    ├── MIGRATION_COMPLETE.md
    ├── REFACTORING_COMPLETE.md
    └── PHASE_5_COMPLETE.md
```

---

## Phase 5: Cleanup & Deletion

### Files to Delete After Migration

**API Files (23 files):**
- All except base.py and __init__.py

**Service Files (25 files):**
- All except base.py

**Model Files (18 files):**
- All (moved to modules)

**Schema Files (11 files):**
- All except validators.py

**Repository Files (6 files):**
- All except base.py

**Root Scripts (14 files):**
- All (moved to scripts/)

**Documentation (40+ files):**
- All (moved to docs/)

**Total: ~100+ files to move/delete**

---

## Phase 6: Testing Strategy

### Test Structure

```
tests/
├── unit/
│   ├── modules/
│   │   ├── users/
│   │   ├── activities/
│   │   ├── fitness_trackers/
│   │   ├── certificates/
│   │   ├── rewards/
│   │   ├── challenges/
│   │   ├── statistics/
│   │   └── gallery/
│   ├── integrations/
│   │   ├── oauth/
│   │   └── payment_gateways/
│   └── core/
│
├── integration/
│   ├── test_users_api.py
│   ├── test_activities_api.py
│   ├── test_fitness_trackers_api.py
│   └── test_oauth_flow.py
│
└── e2e/
    ├── test_user_registration_flow.py
    └── test_event_participation_flow.py
```

### Test Coverage Goals
- Domain Entities: 95%+
- Services: 90%+
- Repositories: 85%+
- API Endpoints: 90%+
- **Overall: 85%+**

---

## Phase 7: Implementation Checklist

### Pre-Migration (1 day)
- [ ] Create feature branch: `feature/ddd-full-migration`
- [ ] Back up production database
- [ ] Create migration tracking spreadsheet
- [ ] Review plan with team

### Wave 1: Foundation (2 weeks)
- [ ] Create users module structure
- [ ] Migrate User model and auth logic
- [ ] Write comprehensive tests
- [ ] Create activities module structure
- [ ] Migrate activity and progress logic
- [ ] Write comprehensive tests

### Wave 2: Fitness Integration (2 weeks)
- [ ] Create fitness_trackers module structure
- [ ] Create Wahoo OAuth provider
- [ ] Create Google Fit OAuth provider
- [ ] Consolidate 6 API files into unified API
- [ ] Test all OAuth flows
- [ ] Delete old provider files

### Wave 3: Feature Modules (2 weeks)
- [ ] Create certificates module
- [ ] Create rewards module (refactor 1,123 lines)
- [ ] Create challenges module
- [ ] Write tests for all

### Wave 4: Support Modules (1 week)
- [ ] Create statistics module
- [ ] Create gallery module
- [ ] Write tests for both

### Integration Consolidation (1 week)
- [ ] Move payment_gateway to integrations/
- [ ] Create external_services directory
- [ ] Move Instagram and Storage services
- [ ] Update all imports

### Root Organization (3 days)
- [ ] Create scripts/ structure
- [ ] Move all 14 root scripts
- [ ] Create docs/ structure
- [ ] Move all 40+ documentation files
- [ ] Create README.md files

### Cleanup (2 days)
- [ ] Delete old app/api/ files
- [ ] Delete old app/services/ files
- [ ] Delete old app/models/ files
- [ ] Delete old app/schemas/ files
- [ ] Delete old app/repositories/ files
- [ ] Remove deprecation layers
- [ ] Update all imports

### Testing & Validation (3 days)
- [ ] Run full test suite
- [ ] Achieve 85%+ coverage
- [ ] Manual testing of critical flows
- [ ] Performance testing
- [ ] Security audit

### Deployment (2 days)
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Monitor for 24 hours
- [ ] Deploy to production
- [ ] Monitor for 48 hours

---

## Phase 8: Risk Mitigation

### Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking imports | High | Medium | Keep backward compatibility during migration |
| OAuth flow breaks | High | Low | Extensive testing before deleting old code |
| Test coverage drops | Medium | Medium | Write tests BEFORE migrating |
| Merge conflicts | Medium | High | Frequent rebases, communication |

### Rollback Strategy

- Complete each wave in separate branch
- Test thoroughly before merging
- Tag release after each wave
- Emergency rollback: `git revert <commit>`

---

## Phase 9: Success Metrics

### Code Quality Metrics

**Before Migration:**
- Total lines: 17,000+
- Largest file: 1,123 lines (rewards.py)
- Duplicate OAuth: 2,600+ lines
- Root docs: 40+ files
- Root scripts: 14 files
- Module structure: 40% migrated

**After Migration Goals:**
- Total lines: <15,000 (10%+ reduction)
- Largest file: <400 lines
- Duplicate OAuth: 0 lines
- Root docs: 0 files
- Root scripts: 0 files
- Module structure: 100% migrated
- Test coverage: 85%+

### Architecture Metrics
- 100% DDD module structure
- 0 business logic in API layer
- All fitness trackers using OAuth framework
- Clear separation: API → Service → Repository → Model
- All commands/queries follow CQRS

---

## Critical Files for Implementation

### 1. app/main.py
**Why:** Central router registration point
**Action:** Update imports from app.api.* to app.modules.*/api/

### 2. app/integrations/oauth/factory.py
**Why:** OAuth provider registration
**Action:** Add Wahoo and Google Fit providers

### 3. app/api/fitness_trackers.py (944 lines)
**Why:** Largest file, needs most refactoring
**Action:** Extract to module, use OAuth framework, reduce to ~300 lines

### 4. app/api/rewards.py (1,123 lines)
**Why:** Second largest, complex fulfillment logic
**Action:** Extract to module, separate services, reduce to ~400 lines

### 5. docs/MODULAR_ARCHITECTURE.md
**Why:** Living architecture documentation
**Action:** Update after each module migration

---

## Summary

This comprehensive DDD migration will transform the glycogrit-backend from a mixed architecture into a clean, maintainable, domain-centric system. The migration is incremental, testable, and safe, with backward compatibility maintained throughout. The end result will be a highly scalable and developer-friendly codebase.

**Key Benefits:**
- ✅ 100% DDD modular architecture
- ✅ 10%+ code reduction through deduplication
- ✅ Unified OAuth framework (eliminates 2,600+ duplicate lines)
- ✅ Organized documentation and scripts
- ✅ 85%+ test coverage
- ✅ Clear domain boundaries
- ✅ Easy onboarding for new developers

**Next Steps:**
1. Review and approve this plan
2. Create feature branch
3. Begin Wave 1: Users module migration
