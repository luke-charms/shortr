# Shortr

A production-grade URL shortener with click analytics, Redis caching, and a background analytics pipeline. Built with FastAPI, PostgreSQL, and Redis.

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [API reference](#api-reference)
- [Getting started](#getting-started)
- [Running tests](#running-tests)
- [Configuration](#configuration)
- [Design decisions](#design-decisions)
- [Development workflow](#development-workflow)

---

## Overview

Shortr turns long URLs into short slugs (e.g. `shortr.io/aB3xK9`) and tracks every click through an asynchronous analytics pipeline. The redirect endpoint is optimised for speed — it reads from Redis first and never blocks on a database write.

**What it does:**

- `POST /api/v1/links` — create a short link with an optional expiry date
- `GET /{slug}` — redirect to the original URL (307), with Redis caching and rate limiting
- `GET /healthz` — liveness probe for load balancers and container orchestrators
- Click events are buffered in Redis and flushed to PostgreSQL every 5 seconds by a background worker

---

## Architecture

```
                         ┌─────────────────────────────────────────┐
                         │              FastAPI app                 │
                         │                                          │
  POST /api/v1/links ───►│  links.py      → LinkRepository         │
                         │                → PostgreSQL              │
                         │                                          │
       GET /{slug}  ───►│  redirects.py  → Redis (cache hit)  ────►│──► 307 Redirect
                         │                → PostgreSQL (miss)       │
                         │                → Redis (analytics queue) │
                         │                                          │
       GET /healthz ───►│  health.py     → 200 OK                  │
                         │                                          │
                         │  analytics_worker  ◄── asyncio task      │
                         │    every 5s: Redis queue → PostgreSQL    │
                         └─────────────────────────────────────────┘

  Redirect hot path:
    1. Rate limit check  (Redis INCR — atomic, ~0.1ms)
    2. Cache lookup      (Redis GET  — ~0.1ms on hit, skips DB entirely)
    3. DB lookup         (PostgreSQL — only on cache miss)
    4. Buffer click      (Redis LPUSH — fire-and-forget, never blocks)
    5. Cache populate    (Redis SET  — so next request is a cache hit)
    6. Return 307
```

The analytics pipeline is **eventually consistent** — clicks appear in the database within ~5 seconds of occurring. This is an intentional trade-off: the redirect endpoint never waits on a database write, keeping latency low regardless of analytics volume.

---

## Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) | Async API, auto OpenAPI docs, dependency injection |
| Database | [PostgreSQL 15](https://www.postgresql.org/) | Persistent storage for links and click events |
| ORM | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) (async) | Database access with typed models |
| Migrations | [Alembic](https://alembic.sqlalchemy.org/) | Version-controlled schema evolution |
| Cache / queue | [Redis 7](https://redis.io/) | URL cache, click counter, click event buffer |
| DB driver | [asyncpg](https://magicstack.github.io/asyncpg/) | Fast async PostgreSQL driver |
| Validation | [Pydantic v2](https://docs.pydantic.dev/) | Request/response schema validation |
| Server | [Uvicorn](https://www.uvicorn.org/) | ASGI server |
| Testing | [pytest](https://pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) + [httpx](https://www.python-httpx.org/) | Async test suite |
| Containerisation | [Docker](https://www.docker.com/) + Compose | Local development stack |
| CI | [GitHub Actions](https://github.com/features/actions) | Lint, migrate, test on every push |

---

## Project structure

```
Shortr/
├── app/
│   ├── api/
│   │   ├── deps.py                  # Shared FastAPI dependencies (get_db)
│   │   ├── health.py                # GET /healthz
│   │   └── v1/
│   │       ├── links.py             # POST /api/v1/links
│   │       └── redirects.py         # GET /{slug}
│   ├── core/
│   │   ├── logging.py               # Structured logger (shared across app)
│   │   └── redis.py                 # Lazy Redis singleton + graceful close
│   ├── db/
│   │   ├── base.py                  # Imports Base + models for Alembic discovery
│   │   ├── base_class.py            # SQLAlchemy DeclarativeBase definition
│   │   ├── session.py               # Async engine and session factory
│   │   └── migrations/              # Alembic migration files
│   │       └── versions/
│   ├── middleware/
│   │   └── timing.py                # Request timing middleware
│   ├── models/
│   │   ├── link.py                  # Link ORM model
│   │   └── click_event.py           # ClickEvent ORM model
│   ├── repositories/
│   │   ├── link_repo.py             # All DB queries for links
│   │   └── click_repo.py            # All DB queries for click events
│   ├── schemas/
│   │   └── link.py                  # Pydantic request/response schemas
│   ├── services/
│   │   ├── analytics.py             # Redis click buffering (INCR + LPUSH)
│   │   ├── cache.py                 # Redis URL cache (GET/SET/DELETE)
│   │   ├── rate_limiter.py          # Per-IP rate limiting (Redis INCR)
│   │   └── shortener.py             # Slug generation
│   ├── workers/
│   │   └── analytics_worker.py      # Background flush: Redis → PostgreSQL
│   └── main.py                      # App factory, lifespan, router registration
├── tests/
│   ├── conftest.py                  # Shared fixtures (DB session, HTTP client, mocks)
│   ├── test_health.py
│   ├── integration/                 # Tests against real DB and Redis
│   │   ├── test_links_api.py
│   │   ├── test_redirect_api.py
│   │   ├── test_expiration.py
│   │   └── test_click_buffering.py
│   └── unit/                        # Tests with mocked dependencies
│       ├── test_cache.py
│       ├── test_click_tracking.py
│       ├── test_deps.py
│       ├── test_link_repo.py
│       ├── test_main.py
│       ├── test_redis.py
│       ├── test_services.py
│       └── test_shortener.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example
├── alembic.ini
├── Makefile
└── pyproject.toml
```

---

## API reference

### `POST /api/v1/links`

Create a short link.

**Request body:**

```json
{
  "url": "https://example.com/some/long/path",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

`expires_at` is optional. Omit it for a permanent link.

**Response `201`:**

```json
{
  "id": 1,
  "url": "https://example.com/some/long/path",
  "slug": "aB3xK9",
  "click_count": 0,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| `422` | Invalid URL or request body |
| `500` | Slug collision exhausted all retries (extremely rare) |

---

### `GET /{slug}`

Redirect to the original URL.

**Response `307`** — Temporary Redirect to the original URL.

**Error responses:**

| Status | Meaning |
|---|---|
| `404` | Slug does not exist |
| `410` | Link has expired |
| `429` | Rate limit exceeded (10 requests per IP per 60 seconds) |

---

### `GET /healthz`

Liveness probe. Returns `200 OK` as long as the application process is running. Does not check database or Redis connectivity.

**Response `200`:**

```json
{ "status": "ok" }
```

---

## Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.11+ (for local development without Docker)

### Quick start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/your-username/shortr.git
cd shortr

# 2. Copy the environment file
cp .env.example .env

# 3. Start the full stack (app + PostgreSQL + Redis)
make docker

# 4. In a separate terminal, run migrations
docker exec shortr_app alembic upgrade head

# The API is now available at http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

### Local development (without Docker)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Copy and edit the environment file
cp .env.example .env
# Set DATABASE_URL and REDIS_URL to point at your local instances

# 4. Run database migrations
alembic upgrade head

# 5. Start the development server
make run
# Server runs at http://localhost:8000 with hot reload
```

### Quick API test

```bash
# Create a short link
curl -X POST http://localhost:8000/api/v1/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Follow the redirect (replace aB3xK9 with your slug)
curl -L http://localhost:8000/aB3xK9

# Check liveness
curl http://localhost:8000/healthz
```

---

## Running tests

Tests require a running PostgreSQL and Redis instance. The `run_tests.sh` script handles this automatically using Docker:

```bash
# Run the full test suite (starts Docker infra, migrates, tests, cleans up)
./run_tests.sh

# Or if you already have Postgres and Redis running locally:
pytest

# Run only unit tests (no infrastructure needed)
pytest tests/unit

# Run only integration tests
pytest tests/integration

# Run without coverage enforcement (faster feedback during development)
pytest --no-cov
```

**Coverage requirement:** the test suite enforces a minimum of 90% code coverage. CI will fail if this threshold is not met.

**Test organisation:**

- `tests/unit/` — all dependencies mocked, no real DB or Redis. Fast, run on every save.
- `tests/integration/` — real PostgreSQL and Redis. Each test runs inside a transaction that is rolled back afterward for isolation.
- `tests/conftest.py` — shared fixtures: session-scoped database engine, per-test rolled-back sessions, HTTP test client, and Redis mocks for the analytics hot path.

---

## Configuration

All configuration is read from environment variables. Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/shortr` | Async PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `APP_ENV` | `development` | Environment name (`development` \| `production` \| `test`) |
| `APP_HOST` | `0.0.0.0` | Uvicorn bind host |
| `APP_PORT` | `8000` | Uvicorn bind port |

**Never commit `.env` to version control.** The `.gitignore` excludes it by default.

---

## Design decisions

### Why Redis for caching?

The redirect endpoint (`GET /{slug}`) is the hottest path in the system — it runs on every single click. A PostgreSQL query on every redirect would create unnecessary load and add 5–20ms of latency per request. Redis lookups take under 1ms and require no connection pool contention with the main application database.

### Why buffer clicks in Redis instead of writing directly to PostgreSQL?

Writing a database row on every redirect would mean the redirect response time is coupled to PostgreSQL write latency. Under load, this creates a feedback loop: more traffic → more DB writes → slower DB → slower redirects → worse user experience.

Instead, clicks are pushed onto a Redis LIST (`LPUSH`) which is a sub-millisecond fire-and-forget operation. A background asyncio task drains this buffer into PostgreSQL every 5 seconds in batches. This introduces ~5 seconds of eventual consistency in analytics data, which is an acceptable trade-off for a significant latency improvement on the hot path.

### Why savepoints for slug collision handling?

When two concurrent requests happen to generate the same slug, a `UNIQUE` constraint violation (`IntegrityError`) is raised. Without savepoints (`begin_nested()`), this error would abort the entire database transaction. With a savepoint, the rollback only undoes the failed INSERT — the transaction stays open, and a new slug can be tried immediately.

### Why is the analytics worker eventually consistent?

Click events flushed from Redis to PostgreSQL may lag by up to the flush interval (default 5 seconds). This is an intentional design choice: the redirect hot path must never wait on a database write. For a URL shortener, knowing click counts to within a few seconds is more than sufficient for analytics purposes. Financial or inventory systems would require a different approach.

### Why `GET /{slug}` returns 307 instead of 301?

`301 Moved Permanently` tells browsers and CDNs to cache the redirect indefinitely. This means if a link expires or the destination URL changes, users' browsers would continue redirecting to the old URL without ever checking back with the server. `307 Temporary Redirect` ensures every redirect goes through the server, allowing expiry checking, analytics recording, and future destination updates.

---

## Development workflow

```bash
# Start infrastructure only (no app container) for local development
docker compose -f docker/docker-compose.yml up db redis -d

# Run the app locally with hot reload
make run

# Create a new database migration after changing a model
alembic revision --autogenerate -m "describe your change here"
alembic upgrade head

# Run the full test suite
./run_tests.sh

# Run tests quickly during development (skips coverage)
pytest --no-cov tests/unit
```

### Branch and commit conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add link expiration support
fix: prevent expired links from being cached in Redis
refactor: extract slug generation into shortener service
test: add integration tests for click buffering pipeline
```

### CI pipeline

Every push to `main` and every pull request runs the full CI pipeline via GitHub Actions:

1. Start PostgreSQL 15 and Redis 7 as service containers
2. Install Python dependencies
3. Run Alembic migrations against the test database
4. Run the full pytest suite with coverage enforcement (≥90%)

The pipeline is defined in `.github/workflows/ci.yml`.

---

## Acknowledgements

Built as a portfolio project to demonstrate production-grade backend engineering patterns: async I/O, database migration discipline, Redis-backed caching and queueing, background worker architecture, and a comprehensive layered test suite.
