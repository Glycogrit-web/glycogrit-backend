---
name: impact-analysis-testing
description: Comprehensive analysis of changes including functionality understanding, impact assessment, and test case creation/improvement
version: 1.0.0
---

# Impact Analysis & Testing Skill

This skill ensures that before making any code changes, Claude thoroughly understands the existing functionality, analyzes the impact on the stable system, and creates/updates comprehensive test cases.

## Purpose

To prevent breaking changes and regressions by:
1. Understanding existing functionality deeply
2. Analyzing impact on the entire system
3. Creating new test cases for new features
4. Updating and improving existing test cases
5. Ensuring test coverage is maintained or improved

## When to Use This Skill

This skill should be invoked **BEFORE** making any significant code changes:
- Adding new features
- Modifying existing functionality
- Refactoring code
- Fixing bugs
- Updating dependencies that affect behavior

## Usage

```bash
# Analyze before making changes to a file
/impact-analysis-testing src/components/ChallengeCard.tsx

# Analyze changes to an API endpoint
/impact-analysis-testing app/api/events.py

# Analyze changes to multiple related files
/impact-analysis-testing src/hooks/useChallenges.ts src/components/Challenges.tsx
```

## Analysis Process

When invoked, this skill follows a structured process:

### Phase 1: Understanding Current Functionality

1. **Read and Analyze the Target Code**
   - Understand what the code currently does
   - Identify all inputs, outputs, and side effects
   - Map dependencies and relationships
   - Document current behavior

2. **Identify Dependencies**
   - Find all files that import this code
   - Find all files this code imports
   - Map data flow and call chains
   - Identify shared state or global effects

3. **Review Existing Tests**
   - Locate test files for this code
   - Analyze what is currently tested
   - Identify test coverage gaps
   - Understand test patterns used

### Phase 2: Impact Analysis

1. **Direct Impact Assessment**
   - What functionality will be added/changed/removed?
   - What existing behavior might break?
   - What edge cases need consideration?
   - What data structures are affected?

2. **Ripple Effect Analysis**
   - Which dependent components are affected?
   - What upstream callers need updates?
   - What downstream consumers are impacted?
   - What database schema changes are needed?
   - What API contracts are affected?

3. **System Stability Analysis**
   - Risk level: Low/Medium/High/Critical
   - Blast radius: Isolated/Module/System/All
   - Rollback complexity
   - Data migration requirements
   - Performance implications

### Phase 3: Test Strategy

1. **New Test Cases Required**
   - Unit tests for new functionality
   - Integration tests for new interactions
   - Edge cases and boundary conditions
   - Error handling scenarios
   - Performance test cases (if needed)

2. **Existing Test Updates**
   - Tests that need modification
   - Tests that need deletion
   - Test data that needs updates
   - Mock/stub updates required

3. **Test Coverage Goals**
   - Current coverage percentage
   - Target coverage percentage
   - Critical paths to cover
   - Regression test additions

### Phase 4: Implementation Plan

1. **Change Breakdown**
   - Ordered steps for implementation
   - Which files to modify first
   - Dependencies between changes
   - Testing checkpoints

2. **Testing Approach**
   - Test-driven or test-after?
   - Test file locations
   - Test framework and patterns
   - CI/CD integration

3. **Validation Strategy**
   - How to verify changes work
   - Manual testing steps
   - Automated test runs
   - Integration testing needs

## Output Format

The skill produces a comprehensive analysis report:

```markdown
# Impact Analysis Report: [Feature/File Name]

## Executive Summary
- **Change Type**: [New Feature/Bug Fix/Refactor/Enhancement]
- **Risk Level**: [Low/Medium/High/Critical]
- **Blast Radius**: [Isolated/Module/System/All]
- **Test Coverage**: Current: X% → Target: Y%

---

## 1. Current Functionality Analysis

### What This Code Does
[Detailed explanation of current behavior]

### Key Functions/Components
- `functionName()` - [Purpose and behavior]
- `ComponentName` - [Purpose and behavior]

### Dependencies
**Imports (Upstream)**:
- `file1.ts` - [How it's used]
- `file2.ts` - [How it's used]

**Imported By (Downstream)**:
- `consumer1.tsx` - [How they use this code]
- `consumer2.ts` - [How they use this code]

### Current Test Coverage
- ✅ Unit tests: [file locations]
- ✅ Integration tests: [file locations]
- ❌ Missing coverage: [gaps identified]

---

## 2. Proposed Changes

### What Will Change
1. [Change description 1]
2. [Change description 2]

### Why This Change
[Rationale and requirements]

---

## 3. Impact Assessment

### Direct Impact
| Component/Function | Current Behavior | New Behavior | Risk |
|-------------------|------------------|--------------|------|
| `functionA()` | [current] | [new] | 🟡 Medium |
| `ComponentB` | [current] | [new] | 🔴 High |

### Ripple Effects

#### Affected Components
1. **`ComponentA.tsx`** (HIGH PRIORITY)
   - **Impact**: [How it's affected]
   - **Required Changes**: [What needs updating]
   - **Test Updates**: [Tests that need modification]

2. **`serviceB.ts`** (MEDIUM PRIORITY)
   - **Impact**: [How it's affected]
   - **Required Changes**: [What needs updating]
   - **Test Updates**: [Tests that need modification]

#### Database Impact
- ❌ No schema changes needed
- ⚠️  Migration required: [migration description]
- ✅ Backward compatible

#### API Contract Impact
- ❌ No API changes
- ⚠️  Breaking change: [description]
- ✅ Backward compatible with versioning

### System Stability Assessment

**Risk Level**: [Low/Medium/High/Critical]

**Reasoning**:
- [Factor 1]
- [Factor 2]

**Mitigation Strategies**:
1. [Strategy 1]
2. [Strategy 2]

**Rollback Plan**:
- [How to undo changes if needed]

---

## 4. Testing Strategy

### New Test Cases Required

#### Unit Tests
```typescript
// Test file: tests/unit/featureName.test.ts

describe('NewFeature', () => {
  it('should handle normal case', () => {
    // Test description
  });

  it('should handle edge case: empty input', () => {
    // Test description
  });

  it('should handle error: invalid data', () => {
    // Test description
  });

  it('should not break existing behavior', () => {
    // Regression test
  });
});
```

#### Integration Tests
```typescript
// Test file: tests/integration/featureFlow.test.ts

describe('Feature Integration', () => {
  it('should work with ComponentA', () => {
    // Integration test
  });
});
```

### Existing Test Updates

| Test File | Update Required | Reason |
|-----------|----------------|--------|
| `test1.test.ts` | Modify | Behavior changed |
| `test2.test.ts` | Delete | No longer relevant |
| `test3.test.ts` | Add cases | Cover new edge cases |

### Test Coverage Goals

**Current Coverage**: X%
**Target Coverage**: Y%

**Critical Paths to Cover**:
1. [Path 1] - [Why critical]
2. [Path 2] - [Why critical]

**Coverage Gaps Identified**:
- ❌ Error handling in `functionA()`
- ❌ Edge case: empty array in `functionB()`
- ❌ Integration with `ServiceC`

---

## 5. Implementation Checklist

### Pre-Implementation
- [ ] Review this impact analysis
- [ ] Discuss with team if risk is High/Critical
- [ ] Create backup branch
- [ ] Document current behavior

### Implementation Order
1. [ ] Update/create test files first (TDD)
2. [ ] Implement changes in [file1]
3. [ ] Update dependent [file2]
4. [ ] Run unit tests
5. [ ] Update integration tests
6. [ ] Run full test suite
7. [ ] Manual testing checklist

### Testing Checkpoints
- [ ] All new tests pass
- [ ] All existing tests still pass
- [ ] No test coverage regression
- [ ] Manual testing completed
- [ ] Edge cases verified
- [ ] Error scenarios tested
- [ ] Performance acceptable

### Post-Implementation
- [ ] Update documentation
- [ ] Update wiki/README if needed
- [ ] Code review completed
- [ ] CI/CD pipeline passes
- [ ] Deployed to staging
- [ ] Smoke tests pass
- [ ] Ready for production

---

## 6. Risk Mitigation

### High-Risk Areas
1. **[Area 1]**
   - **Risk**: [Description]
   - **Mitigation**: [Strategy]
   - **Monitoring**: [How to detect issues]

### Rollback Procedure
1. [Step 1]
2. [Step 2]

### Monitoring Plan
- [ ] Add logging for [specific operation]
- [ ] Add metrics for [performance tracking]
- [ ] Set up alerts for [error conditions]

---

## 7. Questions to Resolve

Before proceeding, clarify:
1. [Question 1]
2. [Question 2]

---

## 8. Alternative Approaches Considered

### Approach A: [Description]
**Pros**: [Benefits]
**Cons**: [Drawbacks]
**Decision**: [Why chosen/not chosen]

### Approach B: [Description]
**Pros**: [Benefits]
**Cons**: [Drawbacks]
**Decision**: [Why chosen/not chosen]

---

## Recommendation

**Proceed**: ✅ / ⚠️  With Caution / ❌ Needs Redesign

**Rationale**: [Why this recommendation]

**Next Steps**:
1. [Action 1]
2. [Action 2]
```

---

## Key Principles

### 1. Always Understand Before Changing
- Read and comprehend existing code fully
- Trace execution paths
- Understand the "why" behind current implementation
- Document assumptions

### 2. Think System-Wide
- Changes rarely affect only one file
- Consider all consumers and dependencies
- Think about data flow across boundaries
- Consider timing and race conditions

### 3. Test Everything
- New features need new tests
- Changed behavior needs updated tests
- Regressions need prevention tests
- Edge cases need explicit tests

### 4. Maintain or Improve Coverage
- Never reduce test coverage
- Aim to improve coverage with each change
- Cover critical paths first
- Test error handling and edge cases

### 5. Plan Before Coding
- Understand impact before implementation
- Have a testing strategy
- Know how to rollback if needed
- Communicate high-risk changes

---

## Test Case Patterns

### Pattern 1: Happy Path Testing
```typescript
describe('Feature', () => {
  it('should work with valid input', () => {
    const result = functionUnderTest(validInput);
    expect(result).toEqual(expectedOutput);
  });
});
```

### Pattern 2: Edge Case Testing
```typescript
describe('Edge Cases', () => {
  it('should handle empty array', () => {
    expect(() => processArray([])).not.toThrow();
  });

  it('should handle null input', () => {
    expect(functionUnderTest(null)).toBe(defaultValue);
  });

  it('should handle very large numbers', () => {
    expect(calculate(Number.MAX_SAFE_INTEGER)).toBeDefined();
  });
});
```

### Pattern 3: Error Handling Testing
```typescript
describe('Error Handling', () => {
  it('should throw on invalid input', () => {
    expect(() => validate(invalidData)).toThrow(ValidationError);
  });

  it('should handle network errors gracefully', () => {
    mockApi.fetchData.mockRejectedValue(new NetworkError());
    expect(getData()).resolves.toBeNull();
  });
});
```

### Pattern 4: Integration Testing
```typescript
describe('Component Integration', () => {
  it('should work with dependency A', () => {
    const componentA = new ComponentA();
    const result = componentB.process(componentA.getData());
    expect(result).toBeDefined();
  });
});
```

### Pattern 5: Regression Testing
```typescript
describe('Regression Tests', () => {
  it('should not break existing behavior after refactor', () => {
    // Test that existed before change
    const result = legacyFunction(legacyInput);
    expect(result).toEqual(expectedLegacyOutput);
  });
});
```

---

## Backend Testing Patterns (Python/FastAPI)

### Pattern 1: API Endpoint Testing
```python
# tests/test_events.py
import pytest
from fastapi.testclient import TestClient

def test_get_events_success(client: TestClient):
    """Test successful event retrieval"""
    response = client.get("/api/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_events_empty(client: TestClient, db_session):
    """Test empty event list"""
    # Clear events
    db_session.query(Event).delete()
    response = client.get("/api/events")
    assert response.status_code == 200
    assert response.json() == []

def test_create_event_validation_error(client: TestClient):
    """Test invalid event creation"""
    invalid_data = {"name": ""}  # Empty name
    response = client.post("/api/events", json=invalid_data)
    assert response.status_code == 422
```

### Pattern 2: Repository Testing
```python
# tests/test_event_repository.py
import pytest
from app.repositories.event_repository import EventRepository

def test_create_event(db_session):
    """Test event creation in database"""
    repo = EventRepository(db_session)
    event = repo.create(
        name="Test Event",
        date="2025-06-01"
    )
    assert event.id is not None
    assert event.name == "Test Event"

def test_get_event_not_found(db_session):
    """Test retrieving non-existent event"""
    repo = EventRepository(db_session)
    event = repo.get_by_id(99999)
    assert event is None

def test_update_event_concurrent_modification(db_session):
    """Test handling concurrent updates"""
    repo = EventRepository(db_session)
    event = repo.create(name="Original")

    # Simulate concurrent modification
    event.name = "Modified 1"
    db_session.flush()

    with pytest.raises(IntegrityError):
        # Second modification should fail
        event.name = "Modified 2"
        db_session.commit()
```

### Pattern 3: Service Layer Testing
```python
# tests/test_event_service.py
import pytest
from app.services.event_service import EventService
from app.exceptions import ValidationError, NotFoundError

def test_register_for_event_success(db_session):
    """Test successful event registration"""
    service = EventService(db_session)
    registration = service.register_for_event(
        user_id=1,
        event_id=1,
        tier="individual"
    )
    assert registration.id is not None
    assert registration.status == "confirmed"

def test_register_for_event_full(db_session):
    """Test registration when event is full"""
    service = EventService(db_session)

    # Fill event to capacity
    event = service.get_event(1)
    event.current_participants = event.max_participants

    with pytest.raises(ValidationError, match="Event is full"):
        service.register_for_event(user_id=2, event_id=1)

def test_register_for_event_duplicate(db_session):
    """Test duplicate registration prevention"""
    service = EventService(db_session)

    # First registration
    service.register_for_event(user_id=1, event_id=1)

    # Duplicate should fail
    with pytest.raises(ValidationError, match="Already registered"):
        service.register_for_event(user_id=1, event_id=1)
```

---

## Frontend Testing Patterns (React/TypeScript)

### Pattern 1: Component Testing
```typescript
// tests/components/ChallengeCard.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChallengeCard } from '@/components/ChallengeCard';

describe('ChallengeCard', () => {
  const mockChallenge = {
    id: 1,
    name: 'Test Challenge',
    description: 'Test description'
  };

  it('should render challenge information', () => {
    render(<ChallengeCard challenge={mockChallenge} />);
    expect(screen.getByText('Test Challenge')).toBeInTheDocument();
  });

  it('should call onJoin when join button clicked', async () => {
    const onJoin = jest.fn();
    render(<ChallengeCard challenge={mockChallenge} onJoin={onJoin} />);

    await userEvent.click(screen.getByRole('button', { name: /join/i }));
    expect(onJoin).toHaveBeenCalledWith(mockChallenge.id);
  });

  it('should disable join button when challenge is full', () => {
    const fullChallenge = { ...mockChallenge, isFull: true };
    render(<ChallengeCard challenge={fullChallenge} />);

    expect(screen.getByRole('button', { name: /full/i })).toBeDisabled();
  });
});
```

### Pattern 2: Custom Hook Testing
```typescript
// tests/hooks/useChallenges.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useChallenges } from '@/hooks/useChallenges';

describe('useChallenges', () => {
  it('should fetch challenges on mount', async () => {
    const { result } = renderHook(() => useChallenges());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.challenges).toBeDefined();
  });

  it('should handle fetch errors', async () => {
    mockApi.fetchChallenges.mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useChallenges());

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });
  });
});
```

---

## Examples

### Example 1: Adding a New Feature

**Scenario**: Adding a "Featured Event" badge to events

**Impact Analysis**:
1. **Direct Impact**:
   - Event model needs `isFeatured` boolean field
   - EventCard component needs badge display
   - API needs to filter/sort featured events

2. **Ripple Effects**:
   - Database migration required
   - Admin panel needs feature toggle
   - Event listing page needs to prioritize featured events
   - Cache invalidation strategy needed

3. **Testing Required**:
   - Unit test: Event model validation
   - Unit test: EventCard renders badge correctly
   - Integration test: Featured events appear first
   - E2E test: Admin can toggle featured status

### Example 2: Fixing a Bug

**Scenario**: User registration fails when phone number is missing

**Impact Analysis**:
1. **Current Behavior**:
   - Code requires phone number (not null)
   - No validation in frontend
   - Backend throws 500 error

2. **Root Cause**:
   - Database schema has NOT NULL constraint
   - Pydantic model requires field
   - No default value

3. **Fix Strategy**:
   - Make phone optional in schema
   - Update Pydantic model
   - Add frontend validation
   - Add backend validation

4. **Testing Required**:
   - Test registration with phone number
   - Test registration without phone number
   - Test validation error messages
   - Regression test: existing registrations still work

---

## Integration with Other Skills

This skill works with:
- **code-quality-guardian**: Ensures quality of changes
- **code-review**: Reviews implementation against standards
- **database-patterns**: Validates database changes

---

## Success Criteria

A successful impact analysis includes:
- ✅ Clear understanding of current functionality
- ✅ Complete dependency mapping
- ✅ Risk assessment with mitigation strategies
- ✅ Comprehensive test strategy
- ✅ Implementation checklist
- ✅ Rollback plan

---

## Anti-Patterns to Avoid

❌ **"Just Make the Change"**
- Don't code first, analyze later
- Don't assume no side effects
- Don't skip testing

❌ **"It's a Small Change"**
- Small changes can have large impacts
- Always analyze dependencies
- Always test edge cases

❌ **"Tests Can Wait"**
- Write tests before or during implementation
- Don't defer testing to "later"
- Don't ship untested code

❌ **"I Know This Code"**
- Always verify assumptions
- Code may have changed since last you saw it
- Dependencies may have evolved

---

## Commands

- `/impact-analysis-testing [file]` - Full analysis
- `/impact-analysis-testing [file] --quick` - Quick impact check
- `/impact-analysis-testing [file] --tests-only` - Focus on testing strategy
- `/impact-analysis-testing [file] --dependencies` - Dependency analysis only

---

## Notes

This skill is MANDATORY before:
- Merging to main branch
- Deploying to production
- Making breaking changes
- Modifying critical paths

Use this skill proactively to prevent bugs and maintain system stability.
