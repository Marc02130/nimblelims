# NimbleLIMS Development Guide

## Cursor Cloud specific instructions

### Architecture Overview

NimbleLIMS is a three-container Docker application (PostgreSQL, FastAPI backend, React frontend) orchestrated by `docker-compose.yml`. See `README.md` for full setup instructions.

### Running the Application

Start all services: `sudo docker compose up -d --build` from the repo root. Services:
- **Database** (lims-db): PostgreSQL 15, port 5432. Alembic migrations run automatically on backend startup.
- **Backend** (lims-backend): FastAPI + Uvicorn, port 8000. API docs at `http://localhost:8000/docs`.
- **Frontend** (lims-frontend): React 18 built via `react-scripts`, served by Nginx, port 3000.

Default logins (development/UAT):
- **Admin**: `admin` / `admin123`
- **Lab Technician**: `lab-tech` / `labtech123`
- **Lab Manager**: `lab-manager` / `labmanager123`
- **Client**: `client` / `client123`

### Important Gotchas

- **Missing `frontend/public/` directory**: The `.gitignore` has a `public` entry (line 154, from a Gatsby template) that gitignores the `frontend/public/` directory. If `frontend/public/index.html` is missing, create it with a standard CRA HTML shell (div id="root"). Without it, the frontend Docker build will fail.
- **Backend tests (`pytest`)**: The `backend/tests/conftest.py` has a pre-existing import bug: line 14 uses `from app.models.user import ...` but models live at `backend/models/`, not `backend/app/models/`. The correct import would be `from models.user import ...`. This blocks all pytest tests from running.
- **Frontend ESLint**: The `.eslintrc.js` extends `@typescript-eslint/recommended` but the correct config path for eslint legacy config is `plugin:@typescript-eslint/recommended`. The `npm run lint` command fails due to this. The `package.json` eslintConfig (`react-app` preset) works fine with `react-scripts`.
- **Frontend tests**: Some Jest tests fail due to MUI X DataGrid v8 compatibility issues with the Jest/JSDOM environment (hash module import errors). About 61 of 116 tests pass.

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
