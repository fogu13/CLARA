# CLARA API — production image (Hetzner VPS behind Caddy; any Docker host works)
#
# Hardening (2026-09): runtime dependencies only (no pytest/ruff in the image),
# unprivileged user, HEALTHCHECK, and a .dockerignore so local .venv/.data/.env
# never land in the layer.
FROM python:3.13-slim

# FORWARDED_ALLOW_IPS: uvicorn only trusts X-Forwarded-* from these peers.
# Caddy and the API share the compose network, so the default is the docker
# bridge range; override with the proxy's address when it lives elsewhere.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FORWARDED_ALLOW_IPS="172.16.0.0/12"

WORKDIR /app

# libpq for psycopg; curl for the container HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer first (cache), runtime extras only.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e "."

# App code, then drop privileges. /app/.data is the SQLite fallback path when
# DATABASE_URL is unset; production sets DATABASE_URL and never writes here.
COPY . .
# Build identity: GET /health and /ready report it, so a smoke run can say
# which commit answered. Pass it at build time:
#   docker compose build --build-arg GIT_COMMIT=$(git -C repo rev-parse --short HEAD)
# (DEPLOY.md release step). Unset = "unknown build", never a guessed commit.
ARG GIT_COMMIT=""
ENV CLARA_BUILD_COMMIT=${GIT_COMMIT}
RUN useradd --system --uid 10001 --create-home clara \
    && mkdir -p /app/.data \
    && chown -R clara:clara /app
USER clara

EXPOSE 8000

# /health is the shallow liveness probe (always cheap); /ready checks the DB.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
