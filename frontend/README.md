# ChangeRadar — Evidence-First Meeting Intelligence (Frontend)

ChangeRadar is a meeting intelligence and temporal delta platform that prepares users for high-stakes meetings by turning developments into traceable, change-aware briefings.

---

## 🎨 Visual Identity: Obsidian & Vermilion

The user interface follows an investigative research design system:
- **Palette**:
  - `--bg-primary: #191918;` (Charcoal canvas)
  - `--bg-secondary: #242321;` (Card containers)
  - `--bg-elevated: #2B2926;` (Inputs & nested panels)
  - `--accent: #E45B3F;` (Vermilion highlights & primary actions)
  - `--accent-hover: #F06A4D;`
  - `--text-primary: #F1EDE5;`
  - `--text-secondary: #A6A096;`
  - `--text-muted: #77736B;`
  - `--border: #393632;`
  - Status tokens: `--success: #65B891;`, `--warning: #E5B45C;`, `--danger: #E45B3F;`, `--info: #83A9D1;`
- **Typography**: Space Grotesk / DM Sans for headings, Inter for UI body, IBM Plex Mono for dates, source IDs, and numerical provenance.
- **Evidence Quality**: Statuses are never conveyed by colour alone; explicit accessible labels (`Supported`, `Contradicted`, `Insufficient`, `Outdated`) accompany all indicators.

---

## 🚀 Key Modules & Pages

1. **Dashboard (`/`)**: Executive overview with metrics, active research sessions, real-time intelligence signals, and evidence health charts.
2. **New Research (`/new`)**: Research subject configuration, scope selection (Personal vs Workspace), time window, custom queries, and baseline explanation.
3. **Research Dossier & Briefing (`/research/:id`)**:
   - Executive briefing overview
   - Event timeline distinguishing event occurrence, publication date, and discovery time
   - Syndication vs independent origin clustering
   - Atomic factual claims ledger with verbatim supporting and contradicting excerpts
   - Personal delta highlighting what changed since the last reviewed baseline
   - Coverage and limitations audit
   - Pre-meeting talking point stress-testing with grounded alternatives
4. **Evidence Ledger (`/evidence`)**: Global repository of claims and primary source documents with stance filtering.
5. **Stress Test (`/stress-test`)**: Defensibility workspace for testing talking points against verified evidence.
6. **Research History (`/history`)**: Catalog of all archived and active dossiers.

---

## ⚙️ Shared Contracts & Integration Boundaries

ChangeRadar frontend adheres strictly to shared contracts agreed with teammates:
- **AI Engine (Surjith)**: Models match `backend/intelligence/contracts.py` and `backend/intelligence/fixtures/sample_result.json`.
- **Backend Platform (Krishank)**: REST endpoints follow `/api/v1/sessions`, `/api/v1/runs`, `/api/v1/sessions/:id/briefing`, and `/api/v1/sessions/:id/stress-tests`.
- **Ownership Scope**: Strict database and UI separation between `PERSONAL` and `WORKSPACE` sessions.

---

## 🛠️ Setup & Local Development

### Prerequisites
- Node.js >= 18.x (v20 or v24 recommended)
- npm or pnpm

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | URL of Krishank's FastAPI backend |
| `VITE_USE_MOCK_DATA` | `true` | When `true`, uses rich sample fixtures for offline/demo evaluation |
| `VITE_POLL_INTERVAL_MS` | `3000` | Polling cadence for active job progress |

### Running the Application

```bash
# Install dependencies
npm install

# Start Vite dev server
npm run dev

# Run unit and component test suite
npm test

# Build production bundle
npm run build
```

---

## 🧪 Mock Mode vs Live Mode

To allow seamless demonstration and testing before backend integration is finalized, ChangeRadar includes an active mock adapter (`src/services/mockData.ts` and `src/services/researchService.ts`):
- Switch dynamically in the UI via the **DATA SOURCE** toggle in the sidebar.
- Toggle between verified multi-angle sample dossiers (Acme Corp, Dr. Elena Rostova, BioSynthetix) and real FastAPI endpoints.

