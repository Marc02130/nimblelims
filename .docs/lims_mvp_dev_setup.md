### Setting Up the Dev Environment on macOS

Based on our planning discussions and the LIMS MVP documents (PRD, User Stories, and Technical Document), the dev environment is designed to be containerized using Docker for consistency across the DB (Postgres), backend (Python/FastAPI), and frontend (React). This aligns with the tech stack in Section 1.3 of the Technical Document and the Docker configuration in Prompt 1 from the Prompts document.

Since you have Cursor (for AI-assisted code generation), Docker, and Python already installed, we'll leverage Cursor to generate the initial project structure via Prompt 1. This will create the folder structure, docker-compose.yml, and basic setup files without writing code yet. We'll use a Python virtual environment on your host machine for any local backend tinkering (e.g., running tests outside Docker), as you mentioned.

Follow these steps sequentially. I'll keep them clear and specific, assuming you're starting from scratch. If you encounter issues (e.g., with Docker permissions on macOS), we can refine iteratively.

#### Step 1: Create the Project Directory and Initialize Git
- Open Terminal on your Mac.
- Create a new directory for the project:
  ```
  mkdir nimblelims
  cd nimblelims
  ```
- Initialize Git for version control (as per best practices in the response style):
  ```
  git init
  ```
- Add a basic `.gitignore` file manually for now (Cursor will enhance it in Prompt 1). Copy this into a new file called `.gitignore` using a text editor like VS Code or nano:
  ```
  # Python
  __pycache__/
  *.py[cod]
  *.pyc
  *.pyo
  *.pyd
  .Python
  *.egg-info/
  *.egg
  dist/
  build/
  *.venv/
  venv/

  # Node.js/React
  node_modules/
  .pnp
  .pnp.js
  .yarn/install-state.gz
  build/
  dist/

  # Docker
  *.dockerignore
  *.log

  # Misc
  .DS_Store
  .env
  *.env
  ```
- Commit the initial setup:
  ```
  git add .gitignore
  git commit -m "Initial commit: Add .gitignore"
  ```

This sets up version control early, as emphasized in our planning guidelines.

#### Step 2: Set Up Python Virtual Environment (Host Machine)
Since you plan to use a virtual environment (useful for installing tools like pytest for local testing or if you need to run backend code outside Docker):
- In Terminal (still in the `nimblelims` directory):
  ```
  python3 -m venv venv
  source venv/bin/activate
  ```
- Upgrade pip and install wheel (basic setup):
  ```
  pip install --upgrade pip wheel
  ```
- For now, don't install project dependencies here—Docker will handle them via `requirements.txt` in the backend container. If we need host-side tools later (e.g., Alembic for migrations), we can add them iteratively.
- To deactivate later: `deactivate`.

Note: This venv is optional for pure Docker dev but aligns with your request.

#### Step 3: Open the Project in Cursor
- Launch Cursor on your Mac.
- Open the `nimblelims` folder in Cursor (File > Open Folder).
- Cursor will index the folder. This is where you'll paste prompts for AI generation.

#### Step 4: Use Cursor to Generate Initial Project Structure (Prompt 1)
- In Cursor, create a new file or open the Composer pane (Cmd+K or the AI prompt interface).
- Copy and paste **Prompt 1** from the Prompts document directly into Cursor's AI prompt:
  ```
  Create the initial project structure for the LIMS MVP based on the Technical Document (sections 1.3, 2.1, 7.2). Include:
  - Root folder with subfolders: backend (Python/FastAPI), frontend (React), db (Postgres migrations/scripts).
  - Docker setup with three containers: 
    - DB: PostgreSQL 15+ (official image, persistent volume for data, env vars for credentials).
    - Backend: Python 3.10+ (install deps like fastapi, uvicorn, sqlalchemy, psycopg2, pyjwt, passlib[bcrypt] via requirements.txt; expose port 8000; depend on DB).
    - Frontend: React 18+ (Node.js 18+; build with npm, serve via Nginx or Node; expose port 3000).
  - docker-compose.yml: Define services, networks, volumes, dependencies (backend waits for DB); include healthchecks.
  - .gitignore: Standard ignores for Python/Node.
  - README.md: Brief setup instructions.
  Ensure PEP8 and ESLint compliance in planning. Do not implement any code yet beyond setup files.
  ```
- Let Cursor generate the files. It should create:
  - Subfolders: `backend/`, `frontend/`, `db/`.
  - Files: `docker-compose.yml`, enhanced `.gitignore`, `README.md`, and basics like `backend/requirements.txt`.
- Review the generated files in Cursor:
  - Check `docker-compose.yml` for services (db, backend, frontend), volumes (e.g., for Postgres data), and env vars (e.g., POSTGRES_USER, POSTGRES_PASSWORD—set secure defaults or use a `.env` file).
  - If anything looks off (e.g., missing healthchecks), you can refine by chatting with Cursor's AI or editing manually.
- Commit the changes in Git:
  ```
  git add .
  git commit -m "Generate initial project structure and Docker setup via Cursor Prompt 1"
  ```

This step implements the Docker configuration from the Technical Document (Section 7.2), with three containers.

#### Step 5: Configure Environment Variables
- Create a `.env` file in the root directory (not committed to Git) for sensitive vars. Add placeholders based on the generated `docker-compose.yml`:
  ```
  POSTGRES_USER=lims_user
  POSTGRES_PASSWORD=securepassword123
  POSTGRES_DB=lims_mvp
  JWT_SECRET_KEY=supersecretkeychangeme
  ```
- Update `docker-compose.yml` if needed to reference these (e.g., via `env_file: .env`).

#### Step 6: Start Docker and Verify the Environment
- Ensure Docker Desktop is running on your Mac (open the app if not).
- In Terminal (in `nimblelims`):
  ```
  docker-compose up -d --build
  ```
  - This builds and starts the containers in detached mode.
  - First run may take time (downloads images, installs deps).
  - **Alembic migrations run automatically** when the backend starts:
    - Creates all database tables
    - Creates initial roles and permissions (including `batch:read`, `batch:manage`, `config:edit`, `test:configure`, `user:manage`, etc.)
    - Creates admin user (username: `admin`, password: `admin123`)
    - Populates initial lists and list entries (normalized to lowercase slug format like `sample_status`)
    - Migration `0008` adds `batch:read` permission if needed
    - Migration `0009` seeds initial analyses (pH Measurement, EPA Method 8080, Total Coliform Enumeration) and analytes (pH, Aldrin, DDT, PCB-1016, Total Coliforms, E. coli) with validation rules
- Verify:
  - Check running containers: `docker ps` (should show three: db, backend, frontend).
  - Check migration logs: `docker logs lims-backend | grep -i migration`
  - Verify admin user exists: `docker exec lims-db psql -U lims_user -d lims_db -c "SELECT username FROM users WHERE username = 'admin';"`
  - Verify seed data: `docker exec lims-db psql -U lims_user -d lims_db -c "SELECT name FROM analyses WHERE active = true;"`
  - Backend: Open browser to `http://localhost:8000/docs` (FastAPI Swagger UI).
  - Frontend: `http://localhost:3000` (React app).
  - Login: Use `admin` / `admin123` at http://localhost:3000
- Logs: `docker-compose logs -f` to monitor all services.
- Stop: `docker-compose down` (add `-v` to remove volumes if you want a fresh start).

If Docker has issues (e.g., port conflicts), common macOS fixes: Ensure no other services on ports 5432 (Postgres), 8000, 3000; increase Docker resources in settings if needed.

#### Step 7: Next Steps in Cursor
Once setup, you can proceed to Prompt 2 in Cursor for the DB schema (e.g., generate SQL scripts and Alembic migrations in `db/`).

This completes the basic dev environment setup, keeping it aligned with our iterative planning. We've tracked this in Git for history.

To refine: Is there a specific part of the Docker setup (e.g., environment variables or healthchecks) you'd like to adjust before moving to the database schema in Prompt 2?