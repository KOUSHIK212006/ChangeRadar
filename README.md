# ChangeRadar — Evidence-First, Change-Aware Meeting Intelligence

> **Know what changed. Understand what matters. Decide what to do.**

ChangeRadar is a meeting intelligence and temporal delta platform that equips decision-makers for high-stakes meetings. It automatically researches entities, tracks developments against reviewed baselines, extracts atomic claims, clusters syndication into independent source origins, identifies contradictions and staleness, and stress-tests proposed talking points against verifiable evidence.

---

## Architecture Overview

ChangeRadar is organized as a unified monorepo containing:

1. **`frontend/`**: React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, Recharts, TanStack Query, and Axios.
   - Built on an investigative **Obsidian & Vermilion** design system.
   - Distinct views for Dossiers, Event Timelines, Evidence Ledger, Personal Delta, Coverage Audits, and Defensibility Stress-Testing.
   - Dual-mode architecture: seamlessly switch between rich offline sample fixtures and live FastAPI endpoints.
2. **`backend/`**: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL / SQLite, and Pydantic v2.
   - Secure JWT authentication with bcrypt password hashing.
   - Strict `PERSONAL` vs `WORKSPACE` tenant isolation.
   - Asynchronous job lifecycle tracking with idempotent worker execution.
3. **`backend/intelligence/`**: Evidence-First Research Intelligence Engine.
   - Parallelized multi-query search (Tavily API).
   - High-efficiency Gemini/Groq LLM pipeline optimized for approximately **4–6 calls per standard run** via semantic batching, while larger runs with expanded article and claim sets scale across additional bounded batches.
   - Pure-Python deterministic normalization, URL domain canonicalization, entity resolution, and temporal delta computation.
   - Strict evidence provenance: distinguishes event occurrence date, publication date, and discovery time; never presents syndication as independent corroboration.

---

## Quickstart & Local Setup

### Prerequisites
- **Python**: 3.10+ (Python 3.10 or 3.11 recommended)
- **Node.js**: 18.x+ (Node 20+ recommended)
- **Package Managers**: `pip` and `npm`

---

### 1. Backend Setup

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
```

#### Running Backend Services

**Terminal 1 — API Server (FastAPI):**
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Root Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- API v1 Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

**Terminal 2 — Background Research Worker:**
```bash
python -m app.worker.service
```

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## Running Verification Tests

### Backend Test Suite (89 Tests)
Run all platform and intelligence engine tests:
```bash
cd backend
python -m pytest tests/ intelligence/tests/ -v
```

### Frontend Test Suite (19 Tests)
Run Vitest component and unit tests:
```bash
cd frontend
npm test -- --run
```

### Frontend Production Build
Validate TypeScript types and build bundle:
```bash
cd frontend
npm run build
```

---

## Key Principles & Evidence Integrity

- **Never Present LLM Confidence as Proof**: Stance and factual assessment are grounded in verifiable, verbatim excerpts with direct source references.
- **Independent Origins vs Syndicated Copies**: Wire syndications (e.g., Bloomberg/Yahoo/Reuters copies) are clustered into a single origin so consensus counts represent genuine multi-source confirmation.
- **Three-Date Temporal Separation**: Event date (when it happened), publication date (when it was reported), and discovery date (when ChangeRadar observed it) are tracked independently.
- **Baseline Awareness**: If an event was already acknowledged before the baseline timestamp, it is never presented as a new development in Personal Delta.
