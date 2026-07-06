# NimbleLIMS Development Guide

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
- **Client**: `client` / `client123`

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
