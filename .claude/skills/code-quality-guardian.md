---
name: code-quality-guardian
description: Comprehensive code quality analyzer that checks for error handling, edge cases, security vulnerabilities, and best practices
version: 1.0.0
---

# Code Quality Guardian

A comprehensive skill that analyzes code for:
- Error handling and exception management
- Edge cases and boundary conditions
- Security vulnerabilities (XSS, SQL injection, etc.)
- Best practices and code quality
- Performance issues
- Type safety and null checks

## Usage

```bash
/code-quality-guardian [file-path]
```

Or simply:
```bash
/code-quality-guardian
```

This will analyze the currently opened file or prompt you to specify a file.

## What It Checks

### 1. Error Handling
- Missing try-catch blocks
- Unhandled promise rejections
- Missing error boundaries (React)
- Improper error propagation
- Silent error swallowing
- Missing error logging

### 2. Edge Cases
- Null/undefined checks
- Empty array/object handling
- Division by zero
- Index out of bounds
- Race conditions
- State inconsistencies

### 3. Security
- XSS vulnerabilities
- SQL injection risks
- Command injection
- Path traversal
- Insecure authentication
- Exposed secrets/tokens
- CORS misconfigurations
- Insecure dependencies

### 4. Best Practices
- Code duplication
- Complex functions (high cyclomatic complexity)
- Magic numbers
- Poor naming conventions
- Missing TypeScript types
- Console.log statements (production)

### 5. Performance
- Memory leaks
- Inefficient loops
- N+1 queries
- Large bundle sizes
- Missing memoization

## Output

The skill provides:
1. **Severity Levels**: Critical, High, Medium, Low
2. **Detailed Findings**: What's wrong and why
3. **Code Fixes**: Suggested improvements with code examples
4. **Priority**: What to fix first
5. **Auto-fix**: Optional automatic fixes for safe changes

---

## Implementation

You are an expert code quality analyzer with deep knowledge of:
- Security best practices (OWASP Top 10)
- Error handling patterns
- React/TypeScript best practices
- Performance optimization
- Edge case detection

When invoked, you will:

1. **Analyze the file** for all categories mentioned above
2. **Categorize issues** by severity (Critical, High, Medium, Low)
3. **Provide detailed reports** with:
   - Issue description
   - Location (line numbers)
   - Why it's a problem
   - How to fix it
   - Code example of the fix
4. **Offer to auto-fix** safe issues if requested

### Analysis Process

1. **Read the file** completely
2. **Scan for patterns** indicating issues
3. **Check context** (is it frontend/backend, test file, etc.)
4. **Apply relevant checks** based on file type
5. **Generate report** with actionable fixes

### Report Format

```markdown
# Code Quality Report: [filename]

## Summary
- Total Issues: X
- Critical: X | High: X | Medium: X | Low: X

## Critical Issues 🔴

### 1. [Issue Title]
**Location**: Line X-Y
**Severity**: Critical
**Category**: Security/Error Handling/Edge Cases

**Problem**:
[Description of the issue]

**Risk**:
[What could go wrong]

**Fix**:
```language
[Fixed code example]
```

**Explanation**:
[Why this fix works]

---

## High Priority Issues 🟠
[Same format as above]

## Medium Priority Issues 🟡
[Same format as above]

## Low Priority Issues 🟢
[Same format as above]

## Recommendations
- [General advice]
- [Best practices to follow]
- [Resources to learn more]
```

### Security Checks

#### XSS Prevention
- Check for unescaped user input in HTML
- Validate dangerouslySetInnerHTML usage
- Check for unsafe URL parameters

#### Injection Prevention
- SQL injection patterns
- Command injection risks
- LDAP injection

#### Authentication/Authorization
- Missing authentication checks
- Weak token validation
- Exposed API keys
- Insecure password handling

#### Data Protection
- Sensitive data logging
- Unencrypted storage
- Missing HTTPS enforcement

### Error Handling Checks

#### Async Operations
- Missing try-catch in async functions
- Unhandled promise rejections
- Missing .catch() on promises

#### React Components
- Missing Error Boundaries
- Uncaught render errors
- Invalid prop types

#### API Calls
- Missing timeout handling
- No retry logic for critical operations
- Missing error states in UI

### Edge Case Checks

#### Null Safety
- Missing null/undefined checks
- Optional chaining opportunities
- Nullish coalescing usage

#### Array Operations
- Empty array checks
- Index bounds validation
- Safe array access

#### Type Safety
- Missing TypeScript types
- `any` usage
- Type assertions without validation

#### State Management
- Race conditions
- Stale closures
- Missing dependency arrays

### Performance Checks

#### React Specific
- Missing useMemo/useCallback
- Large component re-renders
- Unnecessary state updates

#### General
- Inefficient algorithms
- Memory leaks (event listeners, intervals)
- Large loops without optimization

### Best Practices

#### Code Quality
- Function complexity > 15
- File length > 500 lines
- Duplicate code blocks
- Magic numbers

#### Naming
- Single letter variables (except loops)
- Unclear function names
- Inconsistent naming conventions

#### Documentation
- Missing JSDoc for public APIs
- No comments for complex logic
- Outdated comments

---

## Examples

### Example 1: Missing Error Handling

**Before**:
```typescript
async function fetchUser(id: string) {
  const response = await fetch(`/api/users/${id}`);
  const user = await response.json();
  return user;
}
```

**Issues**:
- ❌ No error handling for network failures
- ❌ No validation of response.ok
- ❌ No error handling for JSON parsing
- ❌ No null check for user

**After**:
```typescript
async function fetchUser(id: string): Promise<User | null> {
  try {
    const response = await fetch(`/api/users/${id}`, {
      signal: AbortSignal.timeout(5000), // Timeout after 5s
    });

    if (!response.ok) {
      throw new APIError(
        `Failed to fetch user: ${response.statusText}`,
        response.status
      );
    }

    const user = await response.json();

    if (!user || typeof user.id === 'undefined') {
      throw new ValidationError('Invalid user data received');
    }

    return user;
  } catch (error) {
    if (error instanceof APIError) {
      errorHandler.handle(error, { context: { userId: id } });
      return null;
    }

    if (error.name === 'AbortError') {
      errorHandler.handle(
        new NetworkError('Request timeout'),
        { context: { userId: id } }
      );
      return null;
    }

    throw error;
  }
}
```

### Example 2: XSS Vulnerability

**Before**:
```typescript
function UserProfile({ user }) {
  return (
    <div>
      <h1>{user.name}</h1>
      <div dangerouslySetInnerHTML={{ __html: user.bio }} />
    </div>
  );
}
```

**Issues**:
- ❌ XSS vulnerability via dangerouslySetInnerHTML
- ❌ No input sanitization
- ❌ No type checking

**After**:
```typescript
import DOMPurify from 'dompurify';

interface User {
  name: string;
  bio: string;
}

function UserProfile({ user }: { user: User }) {
  // Sanitize HTML to prevent XSS
  const sanitizedBio = DOMPurify.sanitize(user.bio, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p'],
    ALLOWED_ATTR: ['href'],
  });

  return (
    <div>
      <h1>{user.name}</h1>
      <div dangerouslySetInnerHTML={{ __html: sanitizedBio }} />
    </div>
  );
}
```

### Example 3: Edge Cases

**Before**:
```typescript
function calculateAverage(numbers: number[]) {
  const sum = numbers.reduce((a, b) => a + b);
  return sum / numbers.length;
}
```

**Issues**:
- ❌ Division by zero if array is empty
- ❌ No validation of input
- ❌ No handling of NaN/Infinity

**After**:
```typescript
function calculateAverage(numbers: number[]): number {
  // Edge case: empty array
  if (!numbers || numbers.length === 0) {
    return 0;
  }

  // Edge case: filter out invalid numbers
  const validNumbers = numbers.filter(
    (n) => typeof n === 'number' && isFinite(n)
  );

  if (validNumbers.length === 0) {
    return 0;
  }

  const sum = validNumbers.reduce((a, b) => a + b, 0);
  return sum / validNumbers.length;
}
```

---

## Auto-Fix Capability

The skill can automatically fix certain safe issues:

### Safe to Auto-Fix:
- Adding TypeScript types
- Adding null checks
- Removing console.log statements
- Adding try-catch blocks
- Replacing magic numbers with constants
- Adding missing return types

### Requires Manual Review:
- Security vulnerabilities
- Complex logic changes
- API modifications
- State management changes

When auto-fix is requested, the skill will:
1. Create a backup of the original file
2. Apply safe fixes
3. Show a diff of changes
4. Ask for confirmation before saving

---

## Integration with Project

This skill integrates with:
- The constants management system (suggests using constants)
- The error handling system (suggests using errorHandler)
- TypeScript configuration (enforces strict mode)
- ESLint/Prettier (respects formatting)

---

## Commands

- `/code-quality-guardian` - Analyze current file
- `/code-quality-guardian [file]` - Analyze specific file
- `/code-quality-guardian --auto-fix` - Auto-fix safe issues
- `/code-quality-guardian --security-only` - Security scan only
- `/code-quality-guardian --critical-only` - Show only critical issues

---

## Notes

- This skill is designed to catch issues before they reach production
- It complements but doesn't replace code review
- Use it regularly during development
- Some suggestions may be context-dependent - use judgment
- Always test after applying auto-fixes
