# ── Stage 1: dependency install (cached layer) ───────────────────
FROM python:3.14-slim AS deps

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pull uv binary from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install deps from lockfile before copying source (maximises cache hits)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# ── Stage 2: final image ─────────────────────────────────────────
FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy installed virtualenv from deps stage
COPY --from=deps /app/.venv /app/.venv

# Copy source
COPY . .

# Install the project itself (fast — deps already in .venv)
RUN uv sync --frozen --no-dev

# Ensure persistent-data directories exist
RUN mkdir -p db auth

EXPOSE 8000 8501

# Default: API server (overridden by docker-compose for the ui service)
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
