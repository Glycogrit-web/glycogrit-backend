# Performance Benchmarking Guide

Comprehensive guide for measuring, tracking, and improving performance before, during, and after the modular architecture migration.

---

## Table of Contents

1. [Overview](#overview)
2. [Baseline Metrics](#baseline-metrics)
3. [Benchmarking Tools](#benchmarking-tools)
4. [Key Performance Indicators](#key-performance-indicators)
5. [API Endpoint Benchmarks](#api-endpoint-benchmarks)
6. [Database Query Performance](#database-query-performance)
7. [Memory Usage](#memory-usage)
8. [Load Testing](#load-testing)
9. [Continuous Monitoring](#continuous-monitoring)
10. [Optimization Opportunities](#optimization-opportunities)

---

## Overview

### Why Benchmark?

1. **Validate Refactoring**: Ensure new architecture doesn't degrade performance
2. **Identify Bottlenecks**: Find slow operations before production
3. **Track Progress**: Measure improvements over time
4. **Set Baselines**: Establish performance expectations
5. **Justify Architecture**: Prove benefits of modular approach

### Benchmarking Philosophy

> "If you can't measure it, you can't improve it." - Peter Drucker

- **Baseline First**: Measure current performance before changes
- **Compare Apples to Apples**: Use same data and conditions
- **Realistic Data**: Test with production-like data volumes
- **Multiple Runs**: Average results over 10+ runs
- **Monitor Trends**: Track metrics over time, not just snapshots

---

## Baseline Metrics

### What to Measure BEFORE Migration

Capture these metrics from the **old monolithic architecture** as baseline:

#### 1. API Response Times

```bash
# Measure current API response times
curl -o /dev/null -s -w "Total: %{time_total}s\n" \
  http://localhost:8000/api/payments/123
```

**Target Endpoints**:
- `GET /api/payments/{id}` - Read single payment
- `GET /api/payments/user/{user_id}` - List user payments
- `POST /api/payments/registrations/{id}/create-order` - Create payment order
- `GET /api/registrations/{id}` - Read single registration
- `GET /api/registrations/event/{event_id}` - List event registrations
- `POST /api/registrations/events/{event_id}/tiers/{tier_id}` - Register for event
- `GET /api/events/{id}` - Read single event
- `GET /api/events` - List events with filters

#### 2. Database Query Performance

```sql
-- Enable query timing in PostgreSQL
\timing on

-- Measure key queries
SELECT * FROM payments WHERE id = 123;
SELECT * FROM payments WHERE user_id = 456;
SELECT * FROM registrations WHERE event_id = 1;
SELECT * FROM events WHERE status = 'published';
```

#### 3. Memory Usage

```bash
# Monitor Python process memory
ps aux | grep uvicorn

# More detailed memory profiling
pip install memory_profiler
python -m memory_profiler app/main.py
```

#### 4. Test Suite Execution Time

```bash
# Measure full test suite
time pytest tests/

# Breakdown by test type
time pytest tests/unit/
time pytest tests/integration/
time pytest tests/e2e/
```

### Baseline Recording Template

Create `docs/benchmarks/baseline.md`:

```markdown
# Performance Baseline (Pre-Migration)

**Date**: May 2, 2026
**Version**: v1.5.0 (before modular refactoring)
**Environment**: Local development (16GB RAM, M1 Pro)
**Database**: PostgreSQL 14, 10K registrations, 50K payments

## API Response Times (avg of 10 requests)

| Endpoint | Method | Response Time | Status |
|----------|--------|---------------|--------|
| /api/payments/{id} | GET | 45ms | ✅ |
| /api/payments/user/{user_id} | GET | 320ms | ⚠️ |
| /api/registrations/{id} | GET | 52ms | ✅ |
| /api/registrations/event/{event_id} | GET | 580ms | ⚠️ |
| /api/events | GET | 125ms | ✅ |

## Database Query Times

| Query | Time | Rows |
|-------|------|------|
| SELECT payment by ID | 2ms | 1 |
| SELECT payments by user | 45ms | 150 |
| SELECT registrations by event | 120ms | 500 |

## Memory Usage

- Idle: 180MB
- Under load (100 concurrent): 450MB
- Peak: 620MB

## Test Suite

- Total: 5m 32s
- Unit: 1m 12s
- Integration: 3m 15s
- E2E: 1m 05s
```

---

## Benchmarking Tools

### 1. API Load Testing with Locust

**Installation**:
```bash
pip install locust
```

**File**: `tests/performance/locustfile.py`

```python
from locust import HttpUser, task, between
import random


class GlycoGritUser(HttpUser):
    """Simulate realistic user behavior."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Login user and get token."""
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpass"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)  # Weight: 3x more frequent
    def view_events(self):
        """View list of events."""
        self.client.get("/api/events", headers=self.headers)

    @task(2)
    def view_event_details(self):
        """View single event."""
        event_id = random.randint(1, 100)
        self.client.get(f"/api/events/{event_id}", headers=self.headers)

    @task(1)
    def view_my_registrations(self):
        """View user's registrations."""
        self.client.get("/api/registrations/user/me", headers=self.headers)

    @task(1)
    def view_payment_history(self):
        """View payment history."""
        self.client.get("/api/payments/user/me", headers=self.headers)

    @task(1)
    def create_registration(self):
        """Register for event (write operation)."""
        event_id = random.randint(1, 50)
        tier_id = random.randint(1, 3)
        self.client.post(
            f"/api/registrations/events/{event_id}/tiers/{tier_id}",
            headers=self.headers,
            json={
                "participant_name": "Test User",
                "age": 30,
                "gender": "male",
                "t_shirt_size": "L"
            }
        )
```

**Running Locust**:
```bash
# Start Locust web interface
locust -f tests/performance/locustfile.py

# Or run headless
locust -f tests/performance/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host http://localhost:8000
```

### 2. Database Query Profiling

**Installation**:
```bash
pip install sqlalchemy-utils line_profiler
```

**Query Profiling Script**: `scripts/profile_queries.py`

```python
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.core.database import get_db, engine


class QueryTimer:
    """Track all database queries."""

    def __init__(self):
        self.queries = []

    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())

    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        total = time.time() - conn.info['query_start_time'].pop()
        self.queries.append({
            'statement': statement,
            'parameters': parameters,
            'duration': total
        })


# Enable query profiling
timer = QueryTimer()
event.listen(Engine, "before_cursor_execute", timer.before_cursor_execute)
event.listen(Engine, "after_cursor_execute", timer.after_cursor_execute)


def profile_payment_queries():
    """Profile payment-related queries."""
    from app.modules.payments import PaymentService, GetUserPaymentsQuery

    db = next(get_db())
    service = PaymentService(db)

    # Profile query
    query = GetUserPaymentsQuery(user_id=1, skip=0, limit=10)
    result = service.get_user_payments(query)

    # Print results
    print(f"\n{'='*80}")
    print(f"Payment Queries Profile")
    print(f"{'='*80}\n")

    for i, q in enumerate(timer.queries, 1):
        print(f"Query {i}: {q['duration']*1000:.2f}ms")
        print(f"  SQL: {q['statement'][:100]}...")
        print()

    total_time = sum(q['duration'] for q in timer.queries)
    print(f"Total query time: {total_time*1000:.2f}ms")
    print(f"Number of queries: {len(timer.queries)}")


if __name__ == "__main__":
    profile_payment_queries()
```

### 3. Memory Profiling

**Installation**:
```bash
pip install memory_profiler matplotlib
```

**Memory Profiling Script**: `scripts/profile_memory.py`

```python
from memory_profiler import profile
from app.modules.payments import PaymentService, GetUserPaymentsQuery
from app.core.database import get_db


@profile
def test_payment_memory():
    """Profile memory usage of payment operations."""
    db = next(get_db())
    service = PaymentService(db)

    # Test with large dataset
    query = GetUserPaymentsQuery(user_id=1, skip=0, limit=1000)
    results = service.get_user_payments(query)

    # Process results
    for payment in results:
        _ = payment.amount * 1.18  # Some processing

    return len(results)


if __name__ == "__main__":
    test_payment_memory()
```

**Run**:
```bash
python -m memory_profiler scripts/profile_memory.py
```

### 4. pytest-benchmark for Test Performance

**Installation**:
```bash
pip install pytest-benchmark
```

**Usage in Tests**:
```python
import pytest
from app.modules.payments import PaymentEntity, Payment


def test_payment_entity_is_refundable(benchmark):
    """Benchmark entity property access."""
    payment = Payment(id=1, status="completed", amount=10000)
    entity = PaymentEntity(payment)

    # Benchmark the property
    result = benchmark(lambda: entity.is_refundable)
    assert result is True


def test_payment_service_get_by_id(benchmark, payment_service):
    """Benchmark service method."""
    from app.modules.payments import GetPaymentByIdQuery

    query = GetPaymentByIdQuery(payment_id=1, user_id=1)
    result = benchmark(payment_service.get_payment_by_id, query)
    assert result is not None
```

**Run**:
```bash
# Run benchmarks
pytest tests/unit/modules/payments/ --benchmark-only

# Compare with baseline
pytest --benchmark-compare --benchmark-autosave
```

---

## Key Performance Indicators

### API Response Time Targets

| Category | Target | Warning | Critical |
|----------|--------|---------|----------|
| GET single record | < 50ms | > 100ms | > 200ms |
| GET list (paginated) | < 200ms | > 500ms | > 1000ms |
| POST (create) | < 150ms | > 300ms | > 600ms |
| PUT (update) | < 100ms | > 250ms | > 500ms |
| DELETE | < 100ms | > 250ms | > 500ms |

### Database Query Targets

| Query Type | Target | Warning |
|------------|--------|---------|
| Primary key lookup | < 5ms | > 10ms |
| Index scan | < 20ms | > 50ms |
| Join (2-3 tables) | < 50ms | > 100ms |
| Aggregation | < 100ms | > 200ms |

### Memory Usage Targets

| State | Target | Warning |
|-------|--------|---------|
| Idle | < 200MB | > 300MB |
| Normal load | < 500MB | > 1GB |
| Peak load | < 1GB | > 2GB |

### Test Suite Targets

| Test Type | Target | Warning |
|-----------|--------|---------|
| Unit test (single) | < 10ms | > 50ms |
| Integration test | < 200ms | > 500ms |
| E2E test | < 2s | > 5s |
| Full suite | < 5min | > 10min |

---

## API Endpoint Benchmarks

### Benchmark Script

**File**: `scripts/benchmark_apis.py`

```python
import requests
import time
import statistics
from typing import List, Dict
import json


class APIBenchmark:
    """Benchmark API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = self._get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _get_token(self) -> str:
        """Get authentication token."""
        response = requests.post(f"{self.base_url}/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpass"
        })
        return response.json()["access_token"]

    def benchmark_endpoint(
        self,
        method: str,
        path: str,
        runs: int = 10,
        **kwargs
    ) -> Dict:
        """Benchmark single endpoint."""
        times = []

        for _ in range(runs):
            start = time.time()

            if method.upper() == "GET":
                response = requests.get(
                    f"{self.base_url}{path}",
                    headers=self.headers,
                    **kwargs
                )
            elif method.upper() == "POST":
                response = requests.post(
                    f"{self.base_url}{path}",
                    headers=self.headers,
                    **kwargs
                )

            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

            if response.status_code not in [200, 201]:
                print(f"Warning: {path} returned {response.status_code}")

        return {
            "path": path,
            "method": method,
            "runs": runs,
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0
        }

    def benchmark_suite(self) -> List[Dict]:
        """Run complete benchmark suite."""
        results = []

        # Payment endpoints
        results.append(self.benchmark_endpoint("GET", "/api/payments/1"))
        results.append(self.benchmark_endpoint("GET", "/api/payments/user/me"))

        # Registration endpoints
        results.append(self.benchmark_endpoint("GET", "/api/registrations/1"))
        results.append(self.benchmark_endpoint("GET", "/api/registrations/event/1"))

        # Event endpoints
        results.append(self.benchmark_endpoint("GET", "/api/events/1"))
        results.append(self.benchmark_endpoint("GET", "/api/events"))

        return results

    def print_results(self, results: List[Dict]):
        """Print benchmark results."""
        print("\n" + "="*80)
        print("API Benchmark Results")
        print("="*80 + "\n")

        for r in results:
            status = "✅" if r["mean"] < 200 else "⚠️" if r["mean"] < 500 else "❌"
            print(f"{status} {r['method']} {r['path']}")
            print(f"   Mean: {r['mean']:.2f}ms | Median: {r['median']:.2f}ms")
            print(f"   Min: {r['min']:.2f}ms | Max: {r['max']:.2f}ms")
            print(f"   StdDev: {r['stdev']:.2f}ms\n")

    def save_results(self, results: List[Dict], filename: str):
        """Save results to JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": results
            }, f, indent=2)


if __name__ == "__main__":
    benchmark = APIBenchmark()
    results = benchmark.benchmark_suite()
    benchmark.print_results(results)
    benchmark.save_results(results, "benchmark_results.json")
```

**Run**:
```bash
python scripts/benchmark_apis.py
```

---

## Database Query Performance

### Query Analysis Script

**File**: `scripts/analyze_queries.py`

```python
from sqlalchemy import text
from app.core.database import engine


def analyze_slow_queries():
    """Analyze slow queries in PostgreSQL."""

    # Enable pg_stat_statements extension first
    # In PostgreSQL: CREATE EXTENSION pg_stat_statements;

    query = text("""
        SELECT
            query,
            calls,
            total_exec_time / 1000 as total_time_seconds,
            mean_exec_time / 1000 as mean_time_seconds,
            max_exec_time / 1000 as max_time_seconds
        FROM pg_stat_statements
        WHERE query NOT LIKE '%pg_stat_statements%'
        ORDER BY total_exec_time DESC
        LIMIT 20;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)

        print("\n" + "="*80)
        print("Top 20 Slowest Queries")
        print("="*80 + "\n")

        for row in result:
            print(f"Query: {row.query[:80]}...")
            print(f"  Calls: {row.calls}")
            print(f"  Total time: {row.total_time_seconds:.2f}s")
            print(f"  Mean time: {row.mean_time_seconds*1000:.2f}ms")
            print(f"  Max time: {row.max_time_seconds*1000:.2f}ms\n")


def explain_query(sql: str):
    """EXPLAIN ANALYZE a query."""

    explain_sql = f"EXPLAIN ANALYZE {sql}"

    with engine.connect() as conn:
        result = conn.execute(text(explain_sql))

        print("\n" + "="*80)
        print("Query Plan")
        print("="*80 + "\n")

        for row in result:
            print(row[0])


if __name__ == "__main__":
    analyze_slow_queries()

    # Example: Explain specific query
    explain_query("""
        SELECT * FROM payments
        WHERE user_id = 1
        ORDER BY created_at DESC
        LIMIT 10
    """)
```

### Index Recommendations

Create missing indexes based on common queries:

```sql
-- Payment indexes
CREATE INDEX CONCURRENTLY idx_payments_user_created
  ON payments(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_payments_registration
  ON payments(registration_id);

CREATE INDEX CONCURRENTLY idx_payments_status
  ON payments(status) WHERE status = 'pending';

-- Registration indexes
CREATE INDEX CONCURRENTLY idx_registrations_event_user
  ON registrations(event_id, user_id);

CREATE INDEX CONCURRENTLY idx_registrations_status
  ON registrations(status);

CREATE INDEX CONCURRENTLY idx_registrations_created
  ON registrations(created_at DESC);

-- Event indexes
CREATE INDEX CONCURRENTLY idx_events_status_date
  ON events(status, event_date);

CREATE INDEX CONCURRENTLY idx_events_registration_dates
  ON events(registration_start_date, registration_end_date);

-- Tier indexes
CREATE INDEX CONCURRENTLY idx_tiers_event_active
  ON event_registration_tiers(event_id, is_active);
```

---

## Memory Usage

### Memory Profiling Script

**File**: `scripts/profile_memory_detailed.py`

```python
import tracemalloc
import linecache
import os


def display_top_memory(snapshot, key_type='lineno', limit=10):
    """Display top memory allocations."""

    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))

    top_stats = snapshot.statistics(key_type)

    print(f"\nTop {limit} memory allocations:")
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        filename = os.path.sep.join(frame.filename.split(os.path.sep)[-2:])
        print(f"#{index}: {filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB")

        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print(f"    {line}")

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print(f"Other {len(other)} allocations: {size / 1024:.1f} KiB")

    total = sum(stat.size for stat in top_stats)
    print(f"\nTotal allocated size: {total / 1024:.1f} KiB")


def profile_payment_service():
    """Profile memory usage of payment service."""
    from app.modules.payments import PaymentService, GetUserPaymentsQuery
    from app.core.database import get_db

    # Start tracing
    tracemalloc.start()

    # Take snapshot before
    snapshot_before = tracemalloc.take_snapshot()

    # Run operations
    db = next(get_db())
    service = PaymentService(db)

    for i in range(100):
        query = GetUserPaymentsQuery(user_id=1, skip=0, limit=10)
        results = service.get_user_payments(query)

    # Take snapshot after
    snapshot_after = tracemalloc.take_snapshot()

    # Compare
    top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')

    print("\n" + "="*80)
    print("Memory Allocation Differences")
    print("="*80)

    for stat in top_stats[:10]:
        print(f"{stat}")

    # Display top allocations
    display_top_memory(snapshot_after)

    # Stop tracing
    tracemalloc.stop()


if __name__ == "__main__":
    profile_payment_service()
```

---

## Load Testing

### Load Test Scenarios

**File**: `tests/performance/load_scenarios.py`

```python
from locust import HttpUser, task, between, events
import json


class ReadHeavyUser(HttpUser):
    """Simulate read-heavy workload (80% reads, 20% writes)."""

    wait_time = between(0.5, 2)

    @task(8)
    def read_operations(self):
        endpoints = [
            "/api/events",
            "/api/events/1",
            "/api/registrations/user/me",
            "/api/payments/user/me"
        ]
        import random
        self.client.get(random.choice(endpoints))

    @task(2)
    def write_operations(self):
        self.client.post("/api/registrations/events/1/tiers/1", json={
            "participant_name": "Load Test User",
            "age": 30
        })


class WriteHeavyUser(HttpUser):
    """Simulate write-heavy workload (40% reads, 60% writes)."""

    wait_time = between(1, 3)

    @task(4)
    def read_operations(self):
        self.client.get("/api/events")

    @task(6)
    def write_operations(self):
        # Create registrations
        self.client.post("/api/registrations/events/1/tiers/1", json={
            "participant_name": "Load Test User",
            "age": 30
        })


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before load test."""
    print("Load test starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after load test."""
    print("\nLoad test results:")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failures: {environment.stats.total.num_failures}")
    print(f"RPS: {environment.stats.total.total_rps:.2f}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
```

**Run Load Tests**:
```bash
# Light load (development)
locust -f tests/performance/load_scenarios.py \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 2m

# Medium load (staging)
locust -f tests/performance/load_scenarios.py \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m

# Heavy load (production simulation)
locust -f tests/performance/load_scenarios.py \
  --headless \
  --users 200 \
  --spawn-rate 10 \
  --run-time 10m
```

---

## Continuous Monitoring

### Application Performance Monitoring

**Install APM tools**:
```bash
pip install prometheus-client
pip install opentelemetry-api opentelemetry-sdk
```

**Add Prometheus Metrics**: `app/monitoring/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge
import time


# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Business metrics
payments_created = Counter('payments_created_total', 'Total payments created')
registrations_created = Counter('registrations_created_total', 'Total registrations')
active_registrations = Gauge('active_registrations', 'Current active registrations')


# Middleware to track metrics
from fastapi import Request
import time


async def metrics_middleware(request: Request, call_next):
    """Track request metrics."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    http_request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

### Health Check Endpoint

**File**: `app/api/health.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
import time


router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check with performance metrics."""

    # Check database
    db_start = time.time()
    try:
        db.execute("SELECT 1")
        db_healthy = True
        db_latency = (time.time() - db_start) * 1000
    except Exception as e:
        db_healthy = False
        db_latency = None

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": {
            "healthy": db_healthy,
            "latency_ms": db_latency
        },
        "timestamp": time.time()
    }
```

---

## Optimization Opportunities

### 1. Query Optimization

**Before** (N+1 problem):
```python
# Bad: N+1 queries
registrations = db.query(Registration).filter_by(event_id=1).all()
for reg in registrations:
    tier = db.query(Tier).filter_by(id=reg.tier_id).first()  # N queries!
```

**After** (Eager loading):
```python
# Good: 1 query with JOIN
from sqlalchemy.orm import joinedload

registrations = (
    db.query(Registration)
    .options(joinedload(Registration.tier))
    .filter_by(event_id=1)
    .all()
)
```

### 2. Caching

**Add Redis caching**:
```python
from functools import lru_cache
from redis import Redis

redis_client = Redis(host='localhost', port=6379, decode_responses=True)


def cache_result(key_prefix: str, ttl: int = 300):
    """Cache decorator."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{args}:{kwargs}"

            # Try cache first
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)

            # Compute and cache
            result = func(*args, **kwargs)
            redis_client.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator


@cache_result("event_details", ttl=600)
def get_event_details(event_id: int):
    """Get event with caching."""
    # ... fetch from database
```

### 3. Connection Pooling

**Optimize database pool**:
```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Increase from default 5
    max_overflow=40,       # Allow 40 additional connections
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo_pool=True         # Log pool activity (debug only)
)
```

---

## Comparison Report Template

**File**: `docs/benchmarks/migration_comparison.md`

```markdown
# Performance Comparison: Before vs After Migration

## Summary

| Metric | Before | After | Change | Status |
|--------|--------|-------|--------|--------|
| Avg API Response | 185ms | 142ms | -23% | ✅ Improved |
| P95 Response Time | 520ms | 380ms | -27% | ✅ Improved |
| Memory (idle) | 180MB | 165MB | -8% | ✅ Improved |
| Test Suite Time | 5m 32s | 4m 48s | -13% | ✅ Improved |
| Database Queries/Request | 8.5 | 5.2 | -39% | ✅ Improved |

## Detailed Results

### API Endpoints

| Endpoint | Before | After | Change |
|----------|--------|-------|--------|
| GET /api/payments/{id} | 45ms | 38ms | -16% ✅ |
| GET /api/payments/user/{id} | 320ms | 215ms | -33% ✅ |
| GET /api/registrations/{id} | 52ms | 41ms | -21% ✅ |
| GET /api/registrations/event/{id} | 580ms | 425ms | -27% ✅ |

### Load Test Results (100 concurrent users)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| RPS | 180 | 245 | +36% ✅ |
| Error Rate | 2.3% | 0.8% | -65% ✅ |
| P50 Response | 185ms | 142ms | -23% ✅ |
| P95 Response | 520ms | 380ms | -27% ✅ |
| P99 Response | 850ms | 680ms | -20% ✅ |

## Analysis

The modular architecture migration resulted in **significant performance improvements**:

1. **23% faster average response times** - Better separation of concerns
2. **39% fewer database queries** - Proper repository pattern with eager loading
3. **36% higher throughput** - More efficient service layer
4. **8% lower memory usage** - Better object lifecycle management

## Conclusion

✅ **Migration successful** - All metrics improved, no regressions detected.
```

---

**Version**: 1.0
**Last Updated**: May 2, 2026
**Status**: Complete Benchmarking Guide
