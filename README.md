# LIMS MVP - Laboratory Information Management System

A modern, API-first Laboratory Information Management System built with FastAPI, React, and PostgreSQL.

## Architecture

This project uses a three-container Docker setup:

- **Database (PostgreSQL 15+)**: Data persistence with Row-Level Security
- **Backend (FastAPI + Python 3.10+)**: RESTful API with JWT authentication and RBAC
- **Frontend (React 18+)**: Modern web interface with TypeScript

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nimblelims
   ```

2. **Start the services**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Database: localhost:5432

### Development

#### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend Development
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
nimblelims/
├── backend/                 # FastAPI backend
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile          # Backend container config
│   └── env.example         # Environment variables template
├── frontend/               # React frontend
│   ├── package.json        # Node.js dependencies
│   ├── Dockerfile          # Frontend container config
│   ├── nginx.conf          # Nginx configuration
│   └── .eslintrc.js        # ESLint configuration
├── db/                     # Database setup
│   ├── Dockerfile          # Database container config
│   └── init.sql            # Database initialization
├── docker-compose.yml      # Multi-container orchestration
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Features (MVP Scope)

- **Sample Tracking**: Accessioning, status management, container hierarchy
- **Test Ordering**: Assign analyses to samples with status tracking
- **Results Entry**: Batch-based results entry with validation
- **Security**: JWT authentication with Role-Based Access Control (RBAC)
- **Data Isolation**: Client-specific data access controls

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

## Development Standards

- **Python**: PEP8 compliance with type hints
- **React**: ESLint configuration with TypeScript
- **Database**: Normalized PostgreSQL schema with UUIDs
- **Security**: JWT tokens, bcrypt password hashing, RLS policies

## Environment Variables

Copy `backend/env.example` to `backend/.env` and configure:

- Database connection settings
- JWT secret keys
- Application environment settings

## Health Checks

All containers include health checks:
- Database: PostgreSQL readiness check
- Backend: HTTP endpoint health check
- Frontend: HTTP endpoint health check

## Next Steps

1. Implement database schema with Alembic migrations
2. Create FastAPI models and endpoints
3. Build React components and routing
4. Implement authentication and authorization
5. Add comprehensive testing suite

## Support

Refer to the technical documentation in `.docs/` for detailed implementation specifications.