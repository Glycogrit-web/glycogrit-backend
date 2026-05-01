# Architecture Check Skill

Validates code architecture patterns and project structure adherence.

## Usage

```
/arch-check [component-type] [file-path]
```

## Component Types

- `component` - React component validation
- `hook` - Custom hook validation
- `api` - API client validation
- `config` - Configuration class validation
- `context` - Context provider validation
- `util` - Utility function validation

## Examples

```bash
# Check if a component follows architecture patterns
/arch-check component src/components/ChallengeCard.tsx

# Check if a hook is properly structured
/arch-check hook src/hooks/useChallenges.ts

# Check API client pattern
/arch-check api src/lib/api-client.ts

# Check configuration class
/arch-check config src/lib/config.ts
```

## Validation Rules

### Component Architecture
✅ **Required:**
- Functional component with TypeScript
- Props interface defined
- Proper export pattern
- No business logic (use hooks instead)

✅ **Best Practices:**
- Props destructured at top
- Event handlers use `handle` prefix
- Boolean props use `is/has/should` prefix
- Memoization for expensive operations

❌ **Avoid:**
- Class components
- Inline function definitions in JSX
- Direct API calls (use hooks)
- Complex state logic (use useReducer or custom hook)

### Hook Architecture
✅ **Required:**
- Starts with `use` prefix
- Returns object or array
- Proper TypeScript return type
- Handles loading/error states

✅ **Best Practices:**
- Single responsibility
- Memoized callbacks with useCallback
- Memoized values with useMemo
- Cleanup in useEffect return

❌ **Avoid:**
- Multiple responsibilities
- Missing dependency arrays
- Unmemoized callbacks passed to children

### API Client Architecture
✅ **Required:**
- Singleton pattern
- Private constructor
- Static getInstance method
- Centralized error handling

✅ **Best Practices:**
- TypeScript interfaces for responses
- Custom error classes
- Request/response interceptors
- Retry logic for network errors

❌ **Avoid:**
- Multiple instances
- Scattered error handling
- Inline API calls in components

### Configuration Class Architecture
✅ **Required:**
- Static readonly properties
- No instance creation
- Type-safe values
- Centralized constants

✅ **Best Practices:**
- Validation methods
- Environment-based config
- Grouped by feature
- Documentation comments

❌ **Avoid:**
- Mutable properties
- Magic numbers scattered in code
- Inconsistent naming

### Context Provider Architecture
✅ **Required:**
- Context and Provider exported separately
- Custom hook for consuming context
- Error if used outside provider
- TypeScript types for context value

✅ **Best Practices:**
- Single responsibility per context
- Memoized context value
- Split large contexts
- Performance optimization

❌ **Avoid:**
- Too many values in one context
- Unmemoized context value
- Missing error boundaries

### Utility Function Architecture
✅ **Required:**
- Pure functions (no side effects)
- Explicit TypeScript types
- JSDoc comments
- Unit testable

✅ **Best Practices:**
- Single responsibility
- Descriptive names
- Error handling
- Input validation

❌ **Avoid:**
- Side effects
- Unclear function names
- Missing error handling

## Pattern Examples

### ✅ Good Component Pattern
```typescript
interface ChallengeCardProps {
  challenge: Challenge;
  onSelect?: (id: string) => void;
  isSelected?: boolean;
}

export function ChallengeCard({
  challenge,
  onSelect,
  isSelected = false
}: ChallengeCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(challenge.id);
  }, [challenge.id, onSelect]);

  return (
    <div
      onClick={handleClick}
      className={cn("card", isSelected && "selected")}
    >
      <h3>{challenge.title}</h3>
    </div>
  );
}
```

### ✅ Good Hook Pattern
```typescript
interface UseChallengesReturn {
  challenges: Challenge[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useChallenges(filters?: ChallengeFilters): UseChallengesReturn {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChallenges = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getChallenges(filters);
      setChallenges(data);
    } catch (err) {
      setError(getUserFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchChallenges();
  }, [fetchChallenges]);

  return { challenges, loading, error, refetch: fetchChallenges };
}
```

### ✅ Good Singleton Pattern
```typescript
export class APIClient {
  private static instance: APIClient;
  private baseURL: string;

  private constructor() {
    this.baseURL = Config.API_URL;
  }

  public static getInstance(): APIClient {
    if (!APIClient.instance) {
      APIClient.instance = new APIClient();
    }
    return APIClient.instance;
  }

  async get<T>(endpoint: string): Promise<T> {
    // Implementation
  }
}
```

### ✅ Good Configuration Class
```typescript
export class ChallengeConfig {
  static readonly DEFAULT_PAGE_SIZE = 20;
  static readonly MAX_PAGE_SIZE = 100;
  static readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  static validatePageSize(size: number): number {
    return Math.min(Math.max(size, 1), this.MAX_PAGE_SIZE);
  }
}
```

## Output Format

The skill provides:
1. **Architecture Score**: 0-100
2. **Pattern Compliance**: Which patterns are followed
3. **Violations**: Specific anti-patterns detected
4. **Recommendations**: How to fix issues
5. **Examples**: Code snippets for reference

## References

- [Design Patterns](../wiki/05-Design-Patterns.md)
- [Component Guidelines](../wiki/06-Component-Guidelines.md)
- [State Management](../wiki/07-State-Management.md)
