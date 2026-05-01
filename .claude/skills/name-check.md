# Naming Convention Check Skill

Validates naming conventions across the codebase based on GlycoGrit standards.

## Usage

```
/name-check [path]
```

## Examples

```bash
# Check naming in a specific file
/name-check src/components/ChallengeCard.tsx

# Check naming in a directory
/name-check src/components/

# Check entire project
/name-check
```

## Naming Conventions

### File Naming

| Type | Convention | Example | Pattern |
|------|------------|---------|---------|
| Component | PascalCase | `ChallengeCard.tsx` | `[A-Z][a-zA-Z0-9]*\.tsx` |
| Hook | camelCase + use | `useChallenges.ts` | `use[A-Z][a-zA-Z0-9]*\.ts` |
| Utility | camelCase | `formatDate.ts` | `[a-z][a-zA-Z0-9]*\.ts` |
| Type | PascalCase | `Challenge.ts` | `[A-Z][a-zA-Z0-9]*\.ts` |
| Config | camelCase | `apiConfig.ts` | `[a-z][a-zA-Z0-9]*Config\.ts` |
| Constant | camelCase | `constants.ts` | `[a-z][a-zA-Z0-9]*\.ts` |
| Page | PascalCase | `HomePage.tsx` | `[A-Z][a-zA-Z0-9]*Page\.tsx` |
| Context | PascalCase + Context | `AuthContext.tsx` | `[A-Z][a-zA-Z0-9]*Context\.tsx` |
| Test | match source + .test | `ChallengeCard.test.tsx` | `[A-Za-z0-9]+\.test\.(ts|tsx)` |

### Variable Naming

```typescript
// ✅ Correct
const userName = 'John';                    // camelCase
const MAX_RETRY_COUNT = 3;                 // SCREAMING_SNAKE_CASE for constants
let isLoading = false;                     // boolean: is/has/should prefix
const hasPermission = true;
const shouldRender = false;

// ❌ Incorrect
const user_name = 'John';                  // snake_case
const maxretrycount = 3;                   // no separation
let loading = false;                       // unclear boolean
const UserName = 'John';                   // PascalCase for variables
```

### Function Naming

```typescript
// ✅ Correct
function calculateTotal(items: Item[]): number { }          // camelCase, verb
function getUserById(id: string): User { }                  // get prefix for retrieval
function handleClick(event: Event): void { }                // handle prefix for events
function isValidEmail(email: string): boolean { }           // is prefix for predicates
function formatCurrency(amount: number): string { }         // format prefix for formatting

// ❌ Incorrect
function Calculate_Total(items: Item[]): number { }         // snake_case, PascalCase
function user(id: string): User { }                         // unclear purpose
function onClick(event: Event): void { }                    // missing handle prefix
function validateEmail(email: string): boolean { }          // should be isValidEmail
function currency(amount: number): string { }               // unclear purpose
```

### Component Naming

```typescript
// ✅ Correct
export function ChallengeCard({ challenge }: Props) { }     // PascalCase
export function UserProfileHeader() { }                     // descriptive
export function Button({ children, onClick }: Props) { }    // clear purpose

// ❌ Incorrect
export function challengeCard({ challenge }: Props) { }     // camelCase
export function Header() { }                                // too generic
export function Btn({ children, onClick }: Props) { }       // abbreviated
export function Component1() { }                            // non-descriptive
```

### Props Interface Naming

```typescript
// ✅ Correct
interface ChallengeCardProps {
  challenge: Challenge;
  onSelect?: (id: string) => void;
}

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  isDisabled?: boolean;                    // boolean with prefix
  variant?: 'primary' | 'secondary';
}

// ❌ Incorrect
interface Props {                          // too generic
  challenge: Challenge;
}

interface IChallengeCardProps {            // Hungarian notation
  challenge: Challenge;
}

interface ChallengeCard_Props {            // snake_case
  challenge: Challenge;
}
```

### Hook Naming

```typescript
// ✅ Correct
function useChallenges(filters?: Filters) { }               // use prefix
function useLocalStorage(key: string) { }                   // descriptive
function useDebounce(value: string, delay: number) { }      // clear purpose

// ❌ Incorrect
function challenges(filters?: Filters) { }                  // missing use prefix
function useLS(key: string) { }                            // abbreviated
function hookForDebounce(value: string) { }                // verbose
```

### Type/Interface Naming

```typescript
// ✅ Correct
interface User {                           // PascalCase, singular
  id: string;
  name: string;
}

type ChallengeStatus = 'active' | 'completed' | 'archived';
type ApiResponse<T> = {                    // Generic type
  data: T;
  error: string | null;
};

// ❌ Incorrect
interface user {                           // camelCase
  id: string;
}

interface IUser {                          // Hungarian notation
  id: string;
}

type challenge_status = 'active';          // snake_case
```

### Enum Naming

```typescript
// ✅ Correct
enum UserRole {                            // PascalCase, singular
  Admin = 'ADMIN',                         // PascalCase members
  User = 'USER',
  Guest = 'GUEST',
}

enum ChallengeCategory {
  Running = 'running',
  Cycling = 'cycling',
  Walking = 'walking',
}

// ❌ Incorrect
enum userRole {                            // camelCase
  admin = 'ADMIN',                         // camelCase members
  user = 'USER',
}

enum CHALLENGE_CATEGORY {                  // SCREAMING_SNAKE_CASE
  RUNNING = 'running',
}
```

### Class Naming

```typescript
// ✅ Correct
class APIClient {                          // PascalCase, descriptive
  private baseURL: string;                 // private: camelCase
  public static getInstance() { }          // static: camelCase
  private handleError(error: Error) { }    // private method: camelCase
}

class ChallengeConfig {                    // Configuration class
  static readonly MAX_SIZE = 100;          // static: SCREAMING_SNAKE_CASE
}

// ❌ Incorrect
class apiClient {                          // camelCase
  private base_url: string;                // snake_case
  public static GetInstance() { }          // PascalCase
}

class config {                             // lowercase
  static readonly maxSize = 100;           // camelCase constant
}
```

### Event Handler Naming

```typescript
// ✅ Correct
const handleClick = () => { };             // handle prefix
const handleSubmit = () => { };
const handleChange = (e: Event) => { };
const handleUserSelect = (id: string) => { };

// ❌ Incorrect
const onClick = () => { };                 // missing handle
const click = () => { };                   // unclear
const doSubmit = () => { };                // wrong prefix
const userSelectHandler = () => { };       // verbose
```

### Boolean Naming

```typescript
// ✅ Correct
const isLoading = true;                    // is prefix
const hasPermission = false;               // has prefix
const shouldRender = true;                 // should prefix
const canEdit = false;                     // can prefix
const willUpdate = true;                   // will prefix

// Props
interface Props {
  isVisible: boolean;
  hasError: boolean;
  shouldAutoFocus: boolean;
}

// ❌ Incorrect
const loading = true;                      // no prefix
const permission = false;                  // unclear
const render = true;                       // not boolean-like
const visible = false;                     // ambiguous
```

### Constant Naming

```typescript
// ✅ Correct
const MAX_RETRY_COUNT = 3;                 // SCREAMING_SNAKE_CASE
const API_BASE_URL = 'https://api.example.com';
const DEFAULT_PAGE_SIZE = 20;

// Module-level constants
export const CACHE_DURATION = 5 * 60 * 1000;

// ❌ Incorrect
const maxRetryCount = 3;                   // camelCase
const api_base_url = 'https://api.example.com';  // lowercase
const DefaultPageSize = 20;                // PascalCase
```

### API Route/Endpoint Naming

```typescript
// ✅ Correct
const API_ROUTES = {
  challenges: '/api/challenges',           // lowercase, plural
  challengeById: (id: string) => `/api/challenges/${id}`,  // singular in path
  userProfile: '/api/user/profile',
  auth: {
    login: '/api/auth/login',
    logout: '/api/auth/logout',
  }
};

// ❌ Incorrect
const ApiRoutes = {                        // PascalCase
  Challenges: '/API/CHALLENGES',           // uppercase path
  get_challenge: '/api/GetChallenge',      // inconsistent
};
```

### Directory Naming

```
✅ Correct:
src/
  components/              # lowercase, plural
  hooks/                   # lowercase, plural
  types/                   # lowercase, plural
  utils/                   # lowercase, plural
  lib/                     # lowercase, singular

❌ Incorrect:
src/
  Components/              # PascalCase
  Hook/                    # singular
  Utils/                   # PascalCase
  Lib/                     # PascalCase
```

## Common Patterns

### React Component Pattern
```typescript
// File: ChallengeCard.tsx

interface ChallengeCardProps {
  challenge: Challenge;
  onClick?: () => void;
  isSelected?: boolean;
}

export function ChallengeCard({
  challenge,
  onClick,
  isSelected = false
}: ChallengeCardProps) {
  const handleCardClick = useCallback(() => {
    onClick?.();
  }, [onClick]);

  return (
    <div onClick={handleCardClick}>
      {/* ... */}
    </div>
  );
}
```

### Custom Hook Pattern
```typescript
// File: useChallenges.ts

interface UseChallengesOptions {
  filters?: ChallengeFilters;
  autoFetch?: boolean;
}

interface UseChallengesReturn {
  challenges: Challenge[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useChallenges({
  filters,
  autoFetch = true
}: UseChallengesOptions = {}): UseChallengesReturn {
  // Implementation
}
```

### Singleton Pattern
```typescript
// File: apiClient.ts

class APIClient {
  private static instance: APIClient;
  private readonly baseURL: string;

  private constructor() {
    this.baseURL = process.env.VITE_API_URL!;
  }

  public static getInstance(): APIClient {
    if (!APIClient.instance) {
      APIClient.instance = new APIClient();
    }
    return APIClient.instance;
  }
}

export const apiClient = APIClient.getInstance();
```

## Output Format

The skill checks and reports:
1. **File naming violations**
2. **Variable naming issues**
3. **Function naming problems**
4. **Component naming errors**
5. **Type/Interface naming mistakes**
6. **Suggestions for corrections**

## Severity Levels

- 🔴 **Critical**: Completely wrong convention
- 🟡 **Warning**: Minor deviation from standards
- 🔵 **Info**: Suggestion for improvement

## References

- [Coding Standards](../wiki/01-Coding-Standards.md)
- [Component Guidelines](../wiki/06-Component-Guidelines.md)
