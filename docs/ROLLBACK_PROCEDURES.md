# Rollback Procedures

Comprehensive guide for safely rolling back the modular architecture migration if issues arise.

---

## Table of Contents

1. [Overview](#overview)
2. [When to Rollback](#when-to-rollback)
3. [Rollback Scenarios](#rollback-scenarios)
4. [Rollback Procedures](#rollback-procedures)
5. [Recovery Steps](#recovery-steps)
6. [Database Considerations](#database-considerations)
7. [Testing After Rollback](#testing-after-rollback)
8. [Incident Response](#incident-response)

---

## Overview

### Rollback Philosophy

> "Hope for the best, plan for the worst."

The modular architecture migration was designed with **zero-downtime rollback** in mind:

- **Backward Compatibility**: Old imports still work via re-exports
- **No Schema Changes**: Database structure unchanged
- **Feature Flags**: Can disable new module usage
- **Git Tags**: Every phase has a tagged commit
- **Incremental Migration**: Can rollback individual modules

### Risk Level Assessment

| Migration Phase | Risk | Rollback Difficulty | Downtime |
|----------------|------|---------------------|----------|
| Phase 0: Enums | 🟢 Low | Easy | None |
| Phase 1: Payments | 🟡 Medium | Easy | None |
| Phase 2: Shipping | 🟡 Medium | Easy | None |
| Phase 3: Registrations | 🟠 High | Medium | None |
| Phase 4: Events | 🟡 Medium | Easy | None |
| Phase 5: Integration | 🟢 Low | Easy | None |

---

## When to Rollback

### Critical Issues (Immediate Rollback)

⚠️ **Rollback immediately** if you encounter:

1. **Data Integrity Issues**
   - Payment amounts incorrect
   - Registration status corruption
   - Missing or duplicate records

2. **Critical Bugs**
   - Users cannot register for events
   - Payments failing consistently
   - Shipments not being created

3. **Performance Degradation**
   - Response times > 5x baseline
   - Database connection pool exhaustion
   - Memory leaks causing OOM errors

4. **Production Incidents**
   - Error rate > 5%
   - Customer-facing features broken
   - Revenue-impacting issues

### Warning Signs (Monitor Closely)

⚠️ **Monitor but don't rollback yet**:

1. Slightly increased response times (< 2x baseline)
2. Intermittent errors (< 1% error rate)
3. Increased memory usage (< 50% increase)
4. Non-critical bugs in edge cases

### Success Indicators (No Rollback Needed)

✅ **Migration successful** when:

1. All tests passing (unit, integration, E2E)
2. Response times same or better than baseline
3. Error rate < 0.5%
4. Memory usage stable
5. No customer complaints
6. All critical features working

---

## Rollback Scenarios

### Scenario 1: Rollback During Development

**Situation**: Issue found during local testing or CI

**Impact**: None (not deployed)

**Procedure**:
```bash
# Simply revert Git commits
git log --oneline  # Find commit before migration
git reset --hard <commit-hash>

# Or revert specific file
git checkout <commit-hash> -- path/to/file.py

# Reinstall dependencies if needed
pip install -r requirements.txt
```

### Scenario 2: Rollback Individual Module

**Situation**: One module has issues, others are fine

**Impact**: Minimal (other modules still using new architecture)

**Procedure**:
```bash
# Example: Rollback only Payments module

# 1. Switch to old imports in API routes
# Edit app/api/payments.py
# Change:
from app.modules.payments import PaymentService
# To:
from app.services.payment_service import PaymentService

# 2. Update router registration in main.py
# Comment out new module, uncomment old

# 3. Restart application
systemctl restart glycogrit-backend

# 4. Monitor for 30 minutes
tail -f /var/log/glycogrit/app.log
```

### Scenario 3: Rollback Entire Migration

**Situation**: Multiple issues, need to revert everything

**Impact**: Back to previous stable state

**Procedure**: See [Complete Rollback](#complete-rollback-procedure) below

### Scenario 4: Rollback in Production

**Situation**: Issues discovered after deployment

**Impact**: High (live users affected)

**Procedure**: See [Production Rollback](#production-rollback-procedure) below

---

## Rollback Procedures

### Complete Rollback Procedure

#### Step 1: Stop Application

```bash
# Stop the application server
sudo systemctl stop glycogrit-backend

# Or if using Docker
docker-compose down
```

#### Step 2: Backup Current State

```bash
# Backup current codebase
cd /var/www/glycogrit-backend
tar -czf /backups/glycogrit-$(date +%Y%m%d_%H%M%S).tar.gz .

# Backup database (optional, no schema changes)
pg_dump glycogrit > /backups/glycogrit_db_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 3: Revert Code

```bash
# Option A: Git revert to tagged version
git fetch --tags
git checkout v1.5.0  # Version before migration

# Option B: Git revert commits
git log --oneline -20  # Find migration commits
git revert <commit1> <commit2> <commit3>

# Option C: Restore from backup
cd /var/www/glycogrit-backend
rm -rf *
tar -xzf /backups/glycogrit_backup_pre_migration.tar.gz
```

#### Step 4: Restore Dependencies

```bash
# Restore old requirements
pip install -r requirements.txt --force-reinstall

# Or restore virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 5: Verify Rollback

```bash
# Check Python imports
python -c "from app.services.payment_service import PaymentService; print('OK')"

# Run tests
pytest tests/ -v

# Check for syntax errors
python -m py_compile app/*.py app/**/*.py
```

#### Step 6: Restart Application

```bash
# Restart application
sudo systemctl start glycogrit-backend

# Or with Docker
docker-compose up -d

# Check logs
tail -f /var/log/glycogrit/app.log
```

#### Step 7: Verify Application Health

```bash
# Health check
curl http://localhost:8000/health

# Test critical endpoints
curl http://localhost:8000/api/events
curl http://localhost:8000/api/payments/1
curl http://localhost:8000/api/registrations/1

# Monitor error rate
grep ERROR /var/log/glycogrit/app.log | wc -l
```

### Production Rollback Procedure

#### Pre-Rollback Checklist

- [ ] Incident logged and team notified
- [ ] Root cause identified (if possible)
- [ ] Stakeholders informed of rollback
- [ ] Database backup taken
- [ ] Application backup taken
- [ ] Rollback window scheduled (if possible)

#### Production Rollback Steps

```bash
# 1. Enable maintenance mode (if available)
touch /var/www/glycogrit-backend/MAINTENANCE_MODE

# 2. Stop application gracefully
sudo systemctl stop glycogrit-backend

# 3. Wait for existing requests to complete (30 seconds)
sleep 30

# 4. Revert code to previous version
cd /var/www/glycogrit-backend
git fetch origin
git checkout v1.5.0  # Or: git reset --hard origin/stable

# 5. Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# 6. Run smoke tests
pytest tests/smoke/ -v

# 7. Start application
sudo systemctl start glycogrit-backend

# 8. Verify health
for i in {1..10}; do
  curl -f http://localhost:8000/health || echo "Health check failed"
  sleep 2
done

# 9. Disable maintenance mode
rm /var/www/glycogrit-backend/MAINTENANCE_MODE

# 10. Monitor for 1 hour
tail -f /var/log/glycogrit/app.log | grep -E "ERROR|WARNING"
```

#### Post-Rollback Monitoring

Monitor these metrics for 1 hour after rollback:

```bash
# Error rate
watch -n 10 "grep ERROR /var/log/glycogrit/app.log | wc -l"

# Response times
watch -n 10 "grep 'response_time' /var/log/glycogrit/app.log | tail -20"

# Memory usage
watch -n 10 "ps aux | grep uvicorn | awk '{print \$6}'"

# Active connections
watch -n 10 "netstat -an | grep 8000 | wc -l"
```

---

## Recovery Steps

### After Successful Rollback

1. **Incident Post-Mortem**
   - Document what went wrong
   - Identify root cause
   - Update rollback procedures if needed

2. **Fix Issues**
   - Address bugs in development
   - Add tests to prevent regression
   - Review code changes

3. **Re-Plan Migration**
   - Update migration plan
   - Add additional safeguards
   - Schedule retry with stakeholders

4. **Communication**
   - Update team on lessons learned
   - Document incident in runbook
   - Share knowledge with team

### Rollback Post-Mortem Template

**File**: `docs/incidents/rollback_postmortem_YYYYMMDD.md`

```markdown
# Rollback Post-Mortem: [Date]

## Incident Summary

- **Date**: May 2, 2026
- **Duration**: 45 minutes
- **Severity**: High
- **Impact**: Payment processing affected for 300 users

## Timeline

- **14:00**: Deployed new modular architecture to production
- **14:15**: Alerts triggered for increased error rate
- **14:20**: Issue identified in payment module
- **14:25**: Decision made to rollback
- **14:30**: Rollback initiated
- **14:45**: Rollback completed, service restored

## Root Cause

[Detailed explanation of what caused the issue]

## What Went Wrong

1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

## What Went Right

1. Rollback procedure worked as designed
2. Zero data loss
3. Rollback completed in 15 minutes

## Action Items

1. [ ] Fix bug in payment module
2. [ ] Add integration test for this scenario
3. [ ] Update deployment checklist
4. [ ] Schedule retry deployment

## Lessons Learned

- [Lesson 1]
- [Lesson 2]

## Prevention

How to prevent this in the future:
- [Prevention measure 1]
- [Prevention measure 2]
```

---

## Database Considerations

### No Schema Changes = Easy Rollback

Good news: **The migration doesn't change database schema!**

- ✅ No new tables
- ✅ No altered columns
- ✅ No data migrations
- ✅ Old and new code use same database

### Database Compatibility

Both old and new code work with the same database:

```python
# Old code
from app.models.payment import Payment
payment = db.query(Payment).filter_by(id=1).first()

# New code
from app.modules.payments import Payment
payment = db.query(Payment).filter_by(id=1).first()

# Both work! Payment model is the same.
```

### If You Modified Database

If you made any database changes during migration (not recommended):

```bash
# 1. Identify migrations to rollback
alembic history

# 2. Rollback to previous version
alembic downgrade <revision>

# 3. Verify schema
psql glycogrit -c "\d payments"
```

---

## Testing After Rollback

### Critical Test Suite

Run these tests immediately after rollback:

```bash
# 1. Smoke tests (< 1 minute)
pytest tests/smoke/ -v

# 2. Critical path tests
pytest tests/integration/test_payment_flow.py -v
pytest tests/integration/test_registration_flow.py -v

# 3. API endpoint tests
pytest tests/api/ -k "critical" -v

# 4. Health checks
curl http://localhost:8000/health
curl http://localhost:8000/api/payments/1
curl http://localhost:8000/api/registrations/1
curl http://localhost:8000/api/events
```

### Manual Verification Checklist

- [ ] User can view events
- [ ] User can register for event
- [ ] User can create payment order
- [ ] User can verify payment
- [ ] User can view registration history
- [ ] User can view payment history
- [ ] Admin can view all registrations
- [ ] Admin can view event statistics

### Load Testing After Rollback

```bash
# Quick load test to verify performance
locust -f tests/performance/locustfile.py \
  --headless \
  --users 20 \
  --spawn-rate 5 \
  --run-time 2m \
  --host http://localhost:8000
```

Expected results:
- RPS > 100
- Error rate < 1%
- P95 response time < 500ms

---

## Incident Response

### Incident Severity Levels

#### Severity 1 (Critical)
- Production down
- Payment processing broken
- Data corruption
- Security breach

**Action**: Immediate rollback + emergency response

#### Severity 2 (High)
- Major feature broken
- Significant performance degradation
- Affecting multiple users

**Action**: Rollback within 30 minutes

#### Severity 3 (Medium)
- Minor feature broken
- Affecting few users
- Workaround available

**Action**: Evaluate, may rollback or hotfix

#### Severity 4 (Low)
- UI glitch
- Non-critical feature
- No user impact

**Action**: Fix in next release

### Incident Response Playbook

#### Step 1: Detect (0-5 minutes)
- Monitoring alerts
- Customer reports
- Team discovers issue

#### Step 2: Assess (5-10 minutes)
- Determine severity
- Estimate impact
- Identify affected systems

#### Step 3: Decide (10-15 minutes)
- Rollback vs hotfix?
- Who needs to be notified?
- What's the rollback plan?

#### Step 4: Execute (15-45 minutes)
- Follow rollback procedure
- Monitor progress
- Verify success

#### Step 5: Communicate (Ongoing)
- Notify stakeholders
- Update status page
- Post-mortem after resolution

### Communication Templates

#### Internal Alert (Slack/Teams)
```
🚨 INCIDENT: Production Issue Detected

Severity: HIGH
System: GlycoGrit Backend (Payment Module)
Impact: Users cannot complete payments
Action: Initiating rollback to v1.5.0
ETA: 15 minutes

Incident Commander: @username
War Room: #incident-20260502
```

#### Customer-Facing Status Update
```
We're currently experiencing issues with our payment system.
Our team is working on a fix.

Status: Investigating
Impact: Payment processing may be delayed
ETA: 15 minutes

Updates: https://status.glycogrit.com
```

---

## Rollback Checklist

### Pre-Deployment Checklist

Before deploying migration, ensure:

- [ ] Full test suite passing
- [ ] Load tests completed successfully
- [ ] Database backup taken
- [ ] Code backup/tag created
- [ ] Rollback procedure tested
- [ ] Monitoring dashboards ready
- [ ] Team available for support
- [ ] Stakeholders notified
- [ ] Rollback window identified

### During Rollback Checklist

- [ ] Stop application
- [ ] Backup current state
- [ ] Revert code to previous version
- [ ] Restore dependencies
- [ ] Run smoke tests
- [ ] Restart application
- [ ] Verify health checks
- [ ] Monitor error rates
- [ ] Notify team of completion

### Post-Rollback Checklist

- [ ] Application healthy
- [ ] Error rate normal
- [ ] Response times normal
- [ ] Memory usage normal
- [ ] All critical features working
- [ ] Customer impact resolved
- [ ] Post-mortem scheduled
- [ ] Stakeholders updated

---

## Rollback Scripts

### Automated Rollback Script

**File**: `scripts/rollback.sh`

```bash
#!/bin/bash
set -e  # Exit on error

# Configuration
APP_NAME="glycogrit-backend"
APP_DIR="/var/www/glycogrit-backend"
BACKUP_DIR="/backups"
ROLLBACK_VERSION="${1:-v1.5.0}"

echo "========================================="
echo "GlycoGrit Backend Rollback Script"
echo "========================================="
echo "Rollback version: $ROLLBACK_VERSION"
echo ""

# Step 1: Confirm rollback
read -p "Are you sure you want to rollback to $ROLLBACK_VERSION? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
fi

# Step 2: Stop application
echo "[1/8] Stopping application..."
sudo systemctl stop $APP_NAME || echo "Service not running"

# Step 3: Backup current state
echo "[2/8] Backing up current state..."
cd $APP_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf "$BACKUP_DIR/${APP_NAME}_rollback_${TIMESTAMP}.tar.gz" .

# Step 4: Revert code
echo "[3/8] Reverting code to $ROLLBACK_VERSION..."
git fetch --tags
git checkout $ROLLBACK_VERSION

# Step 5: Restore dependencies
echo "[4/8] Restoring dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# Step 6: Run smoke tests
echo "[5/8] Running smoke tests..."
pytest tests/smoke/ -q || {
    echo "ERROR: Smoke tests failed!"
    exit 1
}

# Step 7: Start application
echo "[6/8] Starting application..."
sudo systemctl start $APP_NAME

# Wait for startup
sleep 5

# Step 8: Verify health
echo "[7/8] Verifying application health..."
for i in {1..10}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Health check passed"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Health check failed after 10 attempts"
        exit 1
    fi
    echo "Waiting for application... ($i/10)"
    sleep 2
done

# Step 9: Final verification
echo "[8/8] Running final verification..."
pytest tests/integration/test_critical_paths.py -q

echo ""
echo "========================================="
echo "✅ Rollback completed successfully!"
echo "========================================="
echo "Version: $ROLLBACK_VERSION"
echo "Backup: $BACKUP_DIR/${APP_NAME}_rollback_${TIMESTAMP}.tar.gz"
echo ""
echo "Please monitor logs for next hour:"
echo "  tail -f /var/log/glycogrit/app.log"
```

**Usage**:
```bash
# Rollback to specific version
./scripts/rollback.sh v1.5.0

# Rollback to previous commit
./scripts/rollback.sh HEAD~1

# Rollback with logging
./scripts/rollback.sh v1.5.0 2>&1 | tee rollback.log
```

---

## Best Practices

### Prevention is Better Than Cure

1. **Thorough Testing**: Test extensively before deployment
2. **Staged Rollout**: Deploy to staging first, then production
3. **Feature Flags**: Use flags to enable/disable modules
4. **Monitoring**: Set up comprehensive monitoring
5. **Small Changes**: Deploy incrementally, not all at once
6. **Rollback Plan**: Have a plan before you need it

### During Migration

1. **Deploy Off-Peak**: Deploy during low-traffic periods
2. **Team Availability**: Ensure team is available for support
3. **Quick Rollback**: Be ready to rollback quickly
4. **Monitor Closely**: Watch metrics during and after deployment
5. **Communication**: Keep stakeholders informed

### After Rollback

1. **Post-Mortem**: Always conduct post-mortem
2. **Document**: Document what happened
3. **Learn**: Share lessons with team
4. **Improve**: Update procedures based on learnings
5. **Re-Plan**: Plan retry with improvements

---

## FAQ

### Q: Will rollback cause data loss?
**A**: No. The migration doesn't change database schema, so rollback is safe.

### Q: How long does rollback take?
**A**: Complete rollback takes 15-30 minutes, depending on environment.

### Q: Can we rollback just one module?
**A**: Yes! Each module is independent and can be rolled back individually.

### Q: What if rollback fails?
**A**: Restore from pre-migration backup. See [Recovery Steps](#recovery-steps).

### Q: Do we need to notify users?
**A**: Only if there's customer-facing impact. Internal rollbacks don't need notification.

### Q: Can we retry migration after rollback?
**A**: Yes! Fix issues, add tests, and redeploy when ready.

---

## Support

### Emergency Contacts

- **DevOps Lead**: [Contact]
- **Backend Lead**: [Contact]
- **On-Call Engineer**: [Contact]

### Resources

- **Monitoring Dashboard**: https://monitoring.glycogrit.com
- **Incident Management**: https://incidents.glycogrit.com
- **Runbook**: https://docs.glycogrit.com/runbook

### Escalation Path

1. **Level 1**: On-call engineer
2. **Level 2**: Backend lead
3. **Level 3**: Engineering manager
4. **Level 4**: CTO

---

**Version**: 1.0
**Last Updated**: May 2, 2026
**Status**: Complete Rollback Guide
**Next Review**: Before production deployment
