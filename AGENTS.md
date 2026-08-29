# NimbleLIMS Development Guide

## Product development process

Full pipeline (proportional), folders, phased implementation, and review handling:

→ **[`.docs/review/development-process/README.md`](.docs/review/development-process/README.md)**

**Docs trees (reorg 2026-08-26):** Everything under **`.docs/`**.  
- **`.docs/review/`** — review spine (stamps, sketches, cycle requirements, process, OQs); prefer committed. Operator how-tos: [`manuals/`](manuals/) ([`HOWTO.md`](manuals/HOWTO.md) plus domain handbooks). Do not put operator manuals back under `.docs/review/manuals/`.  
- **`.docs/internal/`** — working PRDs, specs, design, ideas, user stories, SOP packs, private.  
- **`.docs/discussions/`**, **`.docs/decision-logs/`** — Leadership discussions and stamps.  
See [`.docs/README.md`](.docs/README.md). Do not use the old `.docs-review/` / `.docs-internal/` paths.

**Grok teams:** [`.grok/teams/`](.grok/teams/) — Leadership · BA · Dev · QA · Docs.

Summary:

| Size | Process |
|------|---------|
| **Tiny** | Skip formal docs → implement |
| **Small** | Idea optional → implement |
| **Everything else** | Ideation → requirements → tech sketch → reviews (Lab Ops / CEO / UI / Arch / Security / Scientific CSO / BA / QA) → open questions → implement (with docs + UAT updates) → **docs sync** → **dogfood** → **UAT pass** → **merge to main (production)** → monitor → requirements update |

**Formal review skills:** Lab Ops (`/nimble-lab-ops-review`), CEO (`/nimble-ceo-review`), UI (`/nimble-ui-review`), Architecture (`/nimble-arch-review`), Security CSO (`/nimble-cso-review`), Scientific CSO (`/nimble-scientific-cso-review`), BA (`/nimble-ba-review`), QA (`/nimble-qa-review`). Orchestrator: `/nimble-review-packet`. Artifacts live at `.docs/review/{review-type}-review/{stem}.md`.

**QA review:** Testing / QA Lead (Tobias persona). Testability, UAT readiness, acceptance criteria quality. **Required** for work touching sample tracking / test ordering / results entry / audit / security/RBAC/RLS. Reviews `.docs/review/qa-review/{stem}.md` before implement; not a substitute for post-implement UAT pass. Both are required for full-pipeline work.

**Implement requirements (full-pipeline work):**
1. Documentation sync (manuals / README / `.docs/review/` as applicable)
2. UAT script create-or-update at `UAT_Scripts/uat-{stem}.md`
3. Awareness of QA review conditions (**QA*** prefix) when QA review exists

**UAT pass gate:** Merge to `main` (production) requires UAT pass for full-pipeline features.

## Open questions gate

**Do not start a new phase (or a major feature within a phase) until open questions that block that work are resolved.**

- Living decision logs live under [`.docs/review/open-questions/`](.docs/review/open-questions/) (e.g. experiments: [`.docs/review/open-questions/experiments.md`](.docs/review/open-questions/experiments.md), parsers: [`.docs/review/open-questions/data-parsers-lims-runs.md`](.docs/review/open-questions/data-parsers-lims-runs.md)). Framework stamps also under [`.docs/decision-logs/`](.docs/decision-logs/).
- Checklists (e.g. [`.docs/review/checklist/experiment-checklist.md`](.docs/review/checklist/experiment-checklist.md)) track tasks; **open questions are not owned by the checklist** — they are owned by the open-questions docs.
- Status labels: **Open** (blocks related work), **Decided (provisional)** (shipped temporary rule), **Decided**, **Deferred**.
- If coding surfaces a new product/architecture question, add it to the relevant open-questions doc and **pause** if it blocks the current slice.
- Phases 1–3 of the experiments refactor have shipped (definitions, typed steps, sample journey). Future work still uses the open-questions gate before expanding scope.
- After implement (full pipeline): **docs sync** → **dogfood** → **UAT pass** → **merge to `main`** (production) → monitor → requirements update. See [`.docs/review/development-process/`](.docs/review/development-process/).

## Cursor Cloud specific instructions

### Architecture Overview

NimbleLIMS is a four-container Docker application (PostgreSQL, FastAPI backend, React frontend, R Calculator microservice) orchestrated by `docker-compose.yml`. See `README.md` for full setup instructions.

### Running the Application

Start all services: `sudo docker compose up -d --build` from the repo root. Services:
- **Database** (lims-db): PostgreSQL 15, port 5432. Alembic migrations run automatically on backend startup.
- **Backend** (lims-backend): FastAPI + Uvicorn, port 8000. API docs at `http://localhost:8000/docs`.
- **Frontend** (lims-frontend): React 18 built via `react-scripts`, served by Nginx, port 3000.
- **R Calculator** (lims-r-calculator): Plumber R service for dose-response curve fitting, port 8001 (internal).

Default logins (development/UAT):
- **Admin**: `admin` / `admin123`
- **Lab Technician**: `lab-tech` / `labtech123`
- **Lab Manager**: `lab-manager` / `labmanager123`
- **CRO Partner**: `client` / `client123`

### Important Gotchas

- **Backend tests (`pytest`)**: Tests use `from models.xxx import ...` + `import models` (with PYTHONPATH or cwd set to backend during pytest). The old `app.models` import bug appears fixed in current conftest.py. Use `pytest` with the testcontainer fixtures (they require Docker).
- **Frontend ESLint**: The `.eslintrc.js` extends `@typescript-eslint/recommended` but the correct config path for eslint legacy config is `plugin:@typescript-eslint/recommended`. The `npm run lint` command fails due to this. The `package.json` eslintConfig (`react-app` preset) works fine with `react-scripts`. Use `DISABLE_ESLINT_PLUGIN=true npm run build` to bypass for CI/build verification.
- **Frontend tests**: Some Jest tests fail due to MUI X DataGrid v8 compatibility issues with the Jest/JSDOM environment (hash module import errors). About 61 of 116 tests pass. CustomFieldsManagement.test.tsx needs ongoing updates as Field Management UI evolves (OOB fields, list-backed selects via source lists instead of inline options).
- **Gitignore for frontend/public**: Was causing issues (legacy Gatsby 'public' entry); has been cleaned up to not ignore CRA public/ (index.html, etc.).
- **Field Management UI evolution**: Custom fields now prefer list-backed (source_list from central Lists) for reusability (e.g. same list for Sample top-level + Entry fields). Validation rules still supported for scalars. OOB + Custom shown together, denoted. Legacy admin UIs for /admin/custom-attributes and /admin/name-templates have been fully deleted (no sidebar links, no routes, no pages).

### Development Without Docker

For local backend development:
```
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
DATABASE_URL="<see docker-compose.yml for DB credentials>" python run_server.py
```

For local frontend development:
```
cd frontend && npm install && npm start
```
The frontend dev server proxies `/api/` to the backend via the `nginx.conf` (Docker) or needs `REACT_APP_API_URL` for standalone dev.

### Checking Service Health

```
curl http://localhost:8000/health   # Backend
curl http://localhost:3000          # Frontend
sudo docker ps                     # All containers
sudo docker compose logs -f        # Tail logs
```
