FROM postgres:15-alpine

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/

# Set environment variables for initialization
ENV POSTGRES_DB=lims_db
ENV POSTGRES_USER=lims_user
ENV POSTGRES_PASSWORD=lims_password

# Expose port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD pg_isready -U lims_user -d lims_db || exit 1
