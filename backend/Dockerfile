FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies.
# Build context is the repository root so the R service files can be copied
# for the lock-hash recompute (CALC-REQ-4). There is no Docker socket.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .
COPY services/r-calculator /repo/services/r-calculator
ENV NIMBLELIMS_REPO_ROOT=/repo

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations and start the application
CMD ["./start.sh"]
