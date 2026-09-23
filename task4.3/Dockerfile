# ---- Task 4.3: optimised multi-stage image for the visitor counter ----
ARG PYTHON_VERSION=3.13

# ---------- Stage 1: builder - install dependencies into a virtualenv ----------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: runtime - only the virtualenv and the app code ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

# Runtime defaults; override with -e or --env-file at `docker run`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_NAME="Visitor Counter" \
    APP_ENV=production \
    REDIS_HOST=redis \
    REDIS_PORT=6379

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser main.py .

USER appuser
EXPOSE 8000

# Docker marks the container unhealthy if /health fails (e.g. Redis is down).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "main:get_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]