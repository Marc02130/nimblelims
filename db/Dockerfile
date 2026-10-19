# pgvector image so configuring-agent chunks can store vector(384).
FROM pgvector/pgvector:pg15

# Extensions and the lims schema, then the bootstrap role script.
# Credentials come from Compose, not from this image.
COPY init.sql /docker-entrypoint-initdb.d/init.sql
COPY zz-roles.sh /docker-entrypoint-initdb.d/zz-roles.sh
RUN chmod 755 /docker-entrypoint-initdb.d/zz-roles.sh

EXPOSE 5432

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD pg_isready -d lims_db || exit 1
