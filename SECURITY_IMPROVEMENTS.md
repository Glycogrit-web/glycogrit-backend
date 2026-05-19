# Security Improvements & Audit Report

## Executive Summary

This document provides a comprehensive security audit of the GlycoGrit backend application and recommends critical improvements to enhance security posture.

**Overall Assessment**: The application has a solid security foundation with proper authentication, password hashing, and webhook signature verification. However, several critical improvements are needed.

---

## Current Security Status

### ✅ Strong Points

1. **Password Security**
   - ✅ BCrypt hashing with salt ([app/core/auth.py:19-23](app/core/auth.py#L19-L23))
   - ✅ 72-byte truncation (BCrypt limit respected)
   - ✅ No plaintext password storage

2. **JWT Authentication**
   - ✅ JWT tokens with expiration
   - ✅ Secure token generation
   - ✅ Token validation with error handling

3. **Webhook Security**
   - ✅ HMAC-SHA256 signature verification ([app/api/webhooks.py:21-43](app/api/webhooks.py#L21-L43))
   - ✅ `hmac.compare_digest()` for timing-attack prevention
   - ✅ Rejects webhooks without secrets configured

4. **CORS Protection**
   - ✅ Explicit origin whitelist in production
   - ✅ Wildcard blocked in production ([app/main.py:45-49](app/main.py#L45-L49))

5. **Rate Limiting**
   - ✅ SlowAPI integration
   - ✅ Strict limits on authentication endpoints (5/min)

---

## 🔴 Critical Security Issues

### 1. JWT Token Expiration Too Long

**Severity**: HIGH
**Location**: [app/core/config.py:39](app/core/config.py#L39)

**Current Code**:
```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
```

**Risk**:
- Stolen tokens valid for 7 days
- No token refresh mechanism
- Compromised devices have extended access

**Recommendation**:
```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days

# Implement refresh token system
# Short-lived access tokens (1 hour)
# Long-lived refresh tokens (30 days)
# Refresh tokens stored in database with revocation capability
```

**Implementation Priority**: HIGH

---

### 2. No Account Lockout After Failed Login Attempts

**Severity**: HIGH
**Location**: [app/services/user_service.py:95-135](app/services/user_service.py#L95-L135)

**Current Code**:
```python
def authenticate_user(self, identifier: str, password: str, ...):
    # No failed attempt tracking
    # No account lockout
    if not verify_password(password, user.password_hash):
        raise AuthenticationException("Incorrect email/phone or password")
```

**Risk**:
- Brute force password attacks
- Credential stuffing attacks
- No defense against automated attacks

**Recommendation**:
```python
# Add to User model
failed_login_attempts: int = 0
account_locked_until: Optional[datetime] = None
last_failed_login: Optional[datetime] = None

# In authenticate_user()
if user.account_locked_until and user.account_locked_until > datetime.utcnow():
    raise AuthenticationException(f"Account locked. Try again after {user.account_locked_until}")

if not verify_password(password, user.password_hash):
    user.failed_login_attempts += 1
    user.last_failed_login = datetime.utcnow()

    if user.failed_login_attempts >= 5:
        user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
        logger.warning(f"Account {user.id} locked after {user.failed_login_attempts} failed attempts")

    db.commit()
    raise AuthenticationException("Incorrect email/phone or password")

# Reset on successful login
user.failed_login_attempts = 0
user.account_locked_until = None
```

**Implementation Priority**: HIGH

---

### 3. Missing Security Headers

**Severity**: MEDIUM
**Location**: [app/main.py](app/main.py)

**Current State**: No security headers middleware

**Risk**:
- XSS attacks
- Clickjacking
- MIME sniffing attacks
- No HTTPS enforcement

**Recommendation**:

```python
# Add to app/middleware/security_headers.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # HTTPS enforcement (in production)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Prevent caching of sensitive data
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response

# Add to main.py
app.add_middleware(SecurityHeadersMiddleware)
```

**Implementation Priority**: MEDIUM

---

### 4. Sensitive Data in Logs

**Severity**: MEDIUM
**Location**: Multiple files

**Current Issues**:
```python
# Example risky logging
logger.info(f"User login: {identifier}")  # May log email/phone
logger.error(f"Payment failed: {payment_data}")  # May log card details
logger.debug(f"Webhook payload: {payload}")  # May log sensitive data
```

**Risk**:
- PII exposure in log files
- Compliance violations (GDPR, PCI-DSS)
- Insider threats

**Recommendation**:

```python
# Add to app/core/logging.py
import re

class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from logs"""

    PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        (r'\b\d{10}\b', '[PHONE]'),
        (r'\b\d{16}\b', '[CARD]'),
        (r'"password"\s*:\s*"[^"]*"', '"password":"[REDACTED]"'),
        (r'"token"\s*:\s*"[^"]*"', '"token":"[REDACTED]"'),
    ]

    def filter(self, record):
        message = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        record.msg = message
        return True

# Apply to all loggers
for handler in logging.root.handlers:
    handler.addFilter(SensitiveDataFilter())
```

**Implementation Priority**: MEDIUM

---

### 5. No SQL Injection Protection Verification

**Severity**: MEDIUM
**Current State**: Using SQLAlchemy ORM (good), but need to verify raw queries

**Findings**:
- ✅ Most queries use ORM (safe)
- ⚠️  Some raw SQL with `text()` - needs review
- ⚠️  String formatting in queries - potential risk

**Recommendation**:

Search for risky patterns:
```bash
# Find potential SQL injection risks
grep -r "text(" app/ | grep -v "# safe"
grep -r '\.format(' app/ | grep -E 'query|execute'
grep -r 'f".*SELECT|UPDATE|DELETE|INSERT' app/
```

**Safe Example**:
```python
# ✅ SAFE - Parameterized query
db.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_email}
)

# ❌ UNSAFE - String formatting
db.execute(
    text(f"SELECT * FROM users WHERE email = '{user_email}'")
)
```

**Action**: Audit all `text()` usage and ensure parameterization.

**Implementation Priority**: MEDIUM

---

### 6. Missing Input Validation on Critical Endpoints

**Severity**: MEDIUM
**Location**: Various API endpoints

**Current State**:
- ✅ Pydantic models for basic validation
- ⚠️  Missing business logic validation
- ⚠️  No file upload size limits enforced

**Recommendations**:

```python
# Add to app/schemas/validators.py

from pydantic import validator, Field
import re

class StrictUserRegister(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, regex=r'^\d{10}$')
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)

    @validator('password')
    def password_strength(cls, v):
        """Enforce strong password policy"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')
        return v

    @validator('first_name', 'last_name')
    def no_sql_injection(cls, v):
        """Basic XSS/SQL injection prevention"""
        dangerous = ['<script', 'javascript:', 'onerror=', '--', ';', 'DROP', 'DELETE']
        if any(d in v.lower() for d in dangerous):
            raise ValueError('Invalid characters detected')
        return v.strip()
```

**Implementation Priority**: MEDIUM

---

### 7. Webhook Replay Attack Protection

**Severity**: MEDIUM
**Location**: [app/api/webhooks_v2.py](app/api/webhooks_v2.py)

**Current State**:
- ✅ Event ID tracking implemented
- ✅ Duplicate detection working
- ⚠️  No timestamp validation

**Risk**:
- Old webhooks could be replayed
- No expiration on webhook events

**Recommendation**:

```python
# Add to webhook processing
def validate_webhook_timestamp(webhook_timestamp: str, max_age_seconds: int = 300):
    """Validate webhook timestamp to prevent replay attacks"""
    try:
        webhook_time = datetime.fromisoformat(webhook_timestamp)
        current_time = datetime.utcnow()
        age = (current_time - webhook_time).total_seconds()

        if age > max_age_seconds:
            logger.warning(f"Webhook too old: {age} seconds")
            return False

        if age < -60:  # Future timestamp (clock skew tolerance: 1 min)
            logger.warning(f"Webhook from future: {age} seconds")
            return False

        return True
    except Exception as e:
        logger.error(f"Invalid webhook timestamp: {e}")
        return False

# In webhook handler
if 'timestamp' in payload:
    if not validate_webhook_timestamp(payload['timestamp']):
        raise HTTPException(status_code=400, detail="Webhook expired or invalid timestamp")
```

**Implementation Priority**: LOW

---

### 8. Missing Rate Limiting on Expensive Operations

**Severity**: MEDIUM
**Location**: Various endpoints

**Current State**:
- ✅ Rate limiting on auth endpoints
- ⚠️  No rate limiting on file uploads
- ⚠️  No rate limiting on webhook sync operations

**Recommendation**:

```python
# Add stricter limits
@router.post("/upload")
@limiter.limit("10/hour")  # Strict for file uploads
async def upload_file(...):
    pass

@router.post("/sync")
@limiter.limit("20/hour")  # Prevent abuse of sync
async def sync_activities(...):
    pass

# Add per-user rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_user_id(request: Request):
    # Extract user ID from JWT
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        try:
            payload = decode_access_token(token)
            return payload.get("sub", get_remote_address(request))
        except:
            pass
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_id)
```

**Implementation Priority**: LOW

---

## 🟡 Medium Priority Improvements

### 9. API Key Rotation Policy

**Recommendation**: Implement automatic secret rotation

```python
# Add to app/core/secrets.py
class SecretRotationManager:
    """Manage periodic rotation of secrets"""

    def __init__(self):
        self.rotation_interval_days = 90

    async def check_secret_age(self, secret_name: str):
        # Check if secret older than rotation interval
        # Send alert if rotation needed
        pass

    async def rotate_secret(self, secret_name: str):
        # Generate new secret
        # Update in secret manager (Doppler/Vault)
        # Maintain grace period for old secret
        pass
```

---

### 10. Database Connection Security

**Current**: Using environment variables
**Recommendation**: Use connection encryption

```python
# Add to DATABASE_URL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Verify SSL in database.py
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"sslmode": "require"}  # Force SSL
)
```

---

### 11. Audit Logging for Security Events

**Recommendation**: Log all security-relevant events

```python
# Add to app/models/security_audit_log.py
class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(50))  # login, logout, failed_login, password_change
    user_id = Column(Integer, nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    success = Column(Boolean)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Log security events
def log_security_event(event_type: str, user_id: int, request: Request, success: bool, details: dict = None):
    log = SecurityAuditLog(
        event_type=event_type,
        user_id=user_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        success=success,
        details=details or {}
    )
    db.add(log)
    db.commit()
```

---

### 12. Environment-Specific Security Controls

**Recommendation**: Different security levels per environment

```python
# Add to app/core/config.py
class SecurityConfig:
    # Development
    if ENVIRONMENT == "development":
        REQUIRE_HTTPS = False
        ALLOW_WEAK_PASSWORDS = True
        LOG_LEVEL = "DEBUG"

    # Staging
    elif ENVIRONMENT == "staging":
        REQUIRE_HTTPS = True
        ALLOW_WEAK_PASSWORDS = False
        LOG_LEVEL = "INFO"

    # Production
    elif ENVIRONMENT == "production":
        REQUIRE_HTTPS = True
        ALLOW_WEAK_PASSWORDS = False
        LOG_LEVEL = "WARNING"
        ENABLE_SECURITY_HEADERS = True
        FORCE_MFA = True  # Future: Multi-factor authentication
```

---

## Implementation Roadmap

### Phase 1: Critical (Week 1-2)
- [ ] Reduce JWT token expiration to 1 hour
- [ ] Implement refresh token system
- [ ] Add account lockout after failed logins
- [ ] Add security headers middleware

### Phase 2: High Priority (Week 3-4)
- [ ] Implement sensitive data filtering in logs
- [ ] Audit all raw SQL queries
- [ ] Add password strength validation
- [ ] Add security audit logging

### Phase 3: Medium Priority (Week 5-6)
- [ ] Add webhook timestamp validation
- [ ] Implement per-user rate limiting
- [ ] Add database SSL enforcement
- [ ] Create secret rotation policy

### Phase 4: Enhancement (Week 7-8)
- [ ] Add multi-factor authentication (MFA)
- [ ] Implement session management
- [ ] Add IP whitelisting for admin endpoints
- [ ] Create security monitoring dashboard

---

## Testing Recommendations

### Security Testing Checklist

- [ ] **Authentication Testing**
  - [ ] Test account lockout after 5 failed attempts
  - [ ] Test JWT expiration
  - [ ] Test refresh token flow
  - [ ] Test password reset flow

- [ ] **Authorization Testing**
  - [ ] Test admin-only endpoints as regular user
  - [ ] Test accessing other users' data
  - [ ] Test role-based access control

- [ ] **Input Validation Testing**
  - [ ] Test SQL injection in all input fields
  - [ ] Test XSS in all text inputs
  - [ ] Test file upload size limits
  - [ ] Test invalid data types

- [ ] **Webhook Security Testing**
  - [ ] Test invalid signatures
  - [ ] Test replay attacks
  - [ ] Test expired webhooks
  - [ ] Test malformed payloads

- [ ] **Rate Limiting Testing**
  - [ ] Test auth endpoint rate limits
  - [ ] Test API endpoint rate limits
  - [ ] Test different IP addresses
  - [ ] Test authenticated vs unauthenticated limits

---

## Security Tools Recommendations

### 1. Static Analysis
```bash
# Install Bandit for Python security linting
pip install bandit
bandit -r app/ -f json -o security-report.json

# Install safety for dependency vulnerability scanning
pip install safety
safety check --json
```

### 2. Dependency Scanning
```bash
# Check for known vulnerabilities
pip-audit

# Update dependencies regularly
pip list --outdated
```

### 3. Secret Scanning
```bash
# Install truffleHog for secret detection
pip install truffleHog
trufflehog --regex --entropy=True .
```

### 4. Penetration Testing
- OWASP ZAP for automated scanning
- Burp Suite for manual testing
- SQLMap for SQL injection testing

---

## Compliance Considerations

### GDPR Compliance
- [ ] Right to access (user data export)
- [ ] Right to erasure (user deletion)
- [ ] Data minimization (collect only necessary data)
- [ ] Consent management
- [ ] Data breach notification procedures

### PCI-DSS Compliance (for payments)
- [ ] Never store CVV/CVC codes
- [ ] Tokenize payment data
- [ ] Use PCI-compliant payment gateway
- [ ] Log all payment transactions
- [ ] Encrypt payment data in transit

---

## Monitoring & Alerting

### Critical Alerts
```python
# Add to monitoring system
CRITICAL_ALERTS = {
    "failed_login_spike": "More than 100 failed logins in 5 minutes",
    "account_lockout_spike": "More than 10 accounts locked in 10 minutes",
    "webhook_signature_failures": "More than 50 invalid signatures in 1 hour",
    "unusual_admin_access": "Admin access from new IP/location",
    "database_connection_failure": "Unable to connect to database",
    "high_error_rate": "Error rate > 5% for 5 minutes",
}
```

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [PCI-DSS Standards](https://www.pcisecuritystandards.org/)

---

**Last Updated**: May 19, 2026
**Next Review**: June 19, 2026
**Security Team**: security@glycogrit.com
