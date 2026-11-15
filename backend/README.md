# ChangeRadar Backend & Platform

Backend platform service for ChangeRadar, an AI-powered pre-meeting research intelligence platform.

---

## Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Database:** PostgreSQL (with SQLAlchemy 2.0 ORM & Alembic migrations)
- **Validation & Settings:** Pydantic v2 & Pydantic Settings
- **Testing:** Pytest & HTTPX
- **Deployment:** Docker & Uvicorn

---

## Directory Structure

```text
backend/
├── app/
│   ├── api/                 # Versioned REST endpoints (/api/v1) and dependencies
│   ├── core/                # Database engine, custom exceptions, and error handlers
│   ├── schemas/             # Pydantic schemas (health, errors, common DTOs)
│   ├── config.py            # Environment configuration
│   ├── logging_config.py    # Structured logging configuration
│   └── main.py              # FastAPI application factory & middleware setup
├── tests/                   # Pytest test suite
├── .env.example             # Template for environment variables
├── pyproject.toml           # Project metadata and dependencies
└── requirements.txt         # Pip dependency manifest
```

---

## Quickstart

### 1. Environment Configuration

Copy the example environment file and customize as needed:

```bash
cp .env.example .env
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Run the Development Server

From within the `backend/` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

Access the interactive API documentation:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run the Background Research Worker

The worker daemon runs in a separate process independent from FastAPI. It uses
the fixture provider by default, so local tests and development do not make
paid provider calls.

```bash
python -m app.worker.runner
```

---

## Database Migrations

Configure `DATABASE_URL` in `.env`, then run from the `backend/` directory:

```bash
alembic upgrade head
```

The test suite uses an isolated SQLite database and does not require PostgreSQL.

## Intelligence Providers

`INTELLIGENCE_FIXTURE_MODE=true` is the safe default and loads deterministic
sample output without contacting external services. To enable live research,
set `INTELLIGENCE_FIXTURE_MODE=false` and configure `TAVILY_API_KEY` and
`GROQ_API_KEY`. The engine uses Tavily for search and Groq's OpenAI-compatible
chat completions endpoint for LLM processing. Never put real keys in source
control. Provider calls occur only when a worker processes a job in live mode.

## Running Tests

Install the development dependencies and run both backend suites from `backend/`:

```bash
pip install -r requirements-dev.txt
pytest tests intelligence/tests -v
```

The tests use SQLite, a test-only JWT signing key, and fixture mode; they do not
invoke paid LLM or search APIs.
