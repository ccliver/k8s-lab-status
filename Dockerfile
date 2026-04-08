# syntax=docker/dockerfile:1
# --------------------------------------------------------------------------
# Stage 1: install dependencies with uv
# --------------------------------------------------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first (layer-cached unless pyproject.toml / uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# --------------------------------------------------------------------------
# Stage 2: minimal runtime image
# --------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Non-root user for security
RUN useradd --no-create-home --uid 1001 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "k8s_lab_status.main:app", "--host", "0.0.0.0", "--port", "8000"]
