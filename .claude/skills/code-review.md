# Code Review Skill

Reviews code for adherence to GlycoGrit coding standards, architecture patterns, and best practices.

## Usage

```
/code-review [file-path-or-pattern]
```

## Examples

```bash
# Review a specific file
/code-review src/components/ChallengeCard.tsx

# Review all files in a directory
/code-review src/components/

# Review files matching a pattern
/code-review src/**/*.tsx
```

## What This Skill Checks

### 1. File Naming Conventions
- ✅ Components: PascalCase (e.g., `ChallengeCard.tsx`)
- ✅ Utilities: camelCase (e.g., `formatDate.ts`)
- ✅ Hooks: camelCase with `use` prefix (e.g., `useChallenges.ts`)
- ✅ Types: PascalCase (e.g., `Challenge.ts` or in `types/` folder)
- ✅ Constants: camelCase (e.g., `apiConfig.ts`)

### 2. Component Structure
- ✅ Functional components with TypeScript
- ✅ Props interfaces defined with `Props` suffix
- ✅ Proper component export patterns
- ✅ Hooks at the top of component body
- ✅ Event handlers with `handle` prefix
- ✅ Boolean props with `is/has/should` prefix

### 3. TypeScript Standards
- ✅ Strict mode compliance
- ✅ Explicit return types for functions
- ✅ Interface over type for object shapes
- ✅ Type over interface for unions/intersections
- ✅ Proper generic usage
- ✅ No `any` types (use `unknown` if needed)

### 4. Import Organization
Follows this order:
1. CSS imports
2. React imports
3. Next.js/Framework imports
4. Third-party libraries
5. Type imports (`@/types/`)
6. Config imports (`@/config/`)
7. Lib/utils imports (`@/lib/`, `@/utils/`)
8. Hooks imports (`@/hooks/`)
9. Component imports (`@/components/`)
10. Relative imports (`./`, `../`)

### 5. Code Patterns
- ✅ Singleton pattern for API clients
- ✅ Configuration classes for constants
- ✅ Custom hooks for reusable logic
- ✅ Context providers for global state
- ✅ Error handling with custom error classes
- ✅ Component composition over inheritance

### 6. Best Practices
- ✅ No inline styles (use Tailwind classes)
- ✅ Accessibility attributes (aria-*, role)
- ✅ Semantic HTML elements
- ✅ Proper key props in lists
- ✅ Event handler memoization with useCallback
- ✅ Expensive computations memoized with useMemo
- ✅ No unnecessary state (derive when possible)
- ✅ Functional state updates

### 7. Security
- ✅ No hardcoded secrets or API keys
- ✅ Proper input sanitization
- ✅ No dangerouslySetInnerHTML without sanitization
- ✅ Environment variables properly prefixed

## Output Format

The skill provides:
1. **Overall Score**: Pass/Warning/Fail
2. **Issues Found**: Categorized by severity
3. **Recommendations**: Specific suggestions for improvement
4. **Examples**: Code snippets showing correct patterns

## Severity Levels

- 🔴 **Critical**: Security issues, type safety violations
- 🟡 **Warning**: Naming conventions, code organization
- 🔵 **Info**: Suggestions for optimization, best practices

## References

This skill enforces standards from:
- [Coding Standards](../wiki/01-Coding-Standards.md)
- [Design Patterns](../wiki/05-Design-Patterns.md)
- [Component Guidelines](../wiki/06-Component-Guidelines.md)
- [Security Best Practices](../wiki/04-Security-Best-Practices.md)
