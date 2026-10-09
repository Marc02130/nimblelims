FROM python:3.12-slim-bookworm

# curl: compose healthcheck. Same reason r-calculator installs it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin mcp
USER mcp
EXPOSE 8100
CMD ["nimblelims-mcp"]
