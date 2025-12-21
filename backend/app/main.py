"""
FastAPI application for LIMS MVP
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, samples, tests, containers, batches, results, aliquots, lists, projects, analyses, units
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)
logger.info("=== FASTAPI APPLICATION STARTING ===")

# Database schema is managed by Alembic migrations ONLY
# Run migrations: docker exec lims-backend python run_migrations.py

app = FastAPI(
    title="LIMS MVP API",
    description="Laboratory Information Management System MVP",
    version="1.0.0",
    redirect_slashes=False  # Don't redirect URLs with/without trailing slashes
)

# Request logging middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import sys

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"=== REQUEST: {request.method} {request.url.path} ===", file=sys.stderr, flush=True)
        logger.info(f"=== REQUEST: {request.method} {request.url.path} ===")
        logger.info(f"Query params: {dict(request.query_params)}")
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_str = body.decode()[:500]
                print(f"Body: {body_str}", file=sys.stderr, flush=True)
                logger.info(f"Body: {body_str}")
            except Exception as e:
                print(f"Could not read body: {e}", file=sys.stderr, flush=True)
                logger.warning(f"Could not read body: {e}")
        response = await call_next(request)
        print(f"=== RESPONSE: {response.status_code} ===", file=sys.stderr, flush=True)
        logger.info(f"=== RESPONSE: {response.status_code} ===")
        return response

app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
logger.info("Registering routers...")
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(samples.router, prefix="/samples", tags=["samples"])
app.include_router(tests.router, prefix="/tests", tags=["tests"])
app.include_router(containers.router, prefix="/containers", tags=["containers"])
app.include_router(batches.router, prefix="/batches", tags=["batches"])
app.include_router(results.router, prefix="/results", tags=["results"])
app.include_router(aliquots.router, prefix="/aliquots", tags=["aliquots"])
app.include_router(lists.router, prefix="/lists", tags=["lists"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
app.include_router(units.router, prefix="/units", tags=["units"])
logger.info("All routers registered")

@app.get("/")
async def root():
    print("ROOT ENDPOINT HIT", file=sys.stderr, flush=True)
    return {"message": "LIMS MVP API"}

@app.get("/health")
async def health_check():
    import sys
    print("=" * 50, file=sys.stderr, flush=True)
    print("HEALTH CHECK ENDPOINT CALLED", file=sys.stderr, flush=True)
    print("=" * 50, file=sys.stderr, flush=True)
    return {"status": "healthy"}

@app.get("/test-log")
async def test_log():
    import sys
    import os
    sys.stderr.write("=" * 50 + "\n")
    sys.stderr.write("TEST LOG ENDPOINT CALLED - IF YOU SEE THIS, LOGGING WORKS\n")
    sys.stderr.write("=" * 50 + "\n")
    sys.stderr.flush()
    # Also write to a file to be absolutely sure
    with open("/tmp/backend-test.log", "a") as f:
        f.write("TEST ENDPOINT CALLED\n")
        f.flush()
    return {"message": "Check docker logs - you should see the message above"}

@app.post("/test-login")
async def test_login_endpoint():
    import sys
    sys.stderr.write("=" * 50 + "\n")
    sys.stderr.write("TEST LOGIN ENDPOINT HIT\n")
    sys.stderr.write("=" * 50 + "\n")
    sys.stderr.flush()
    return {"test": "login endpoint works"}
