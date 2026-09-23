"""Task 4.3 - Visitor counter web app (FastAPI + Redis) for Docker deployment."""

import html
import os
import socket
from dataclasses import dataclass

import redis
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

DEFAULT_APP_NAME = "Visitor Counter"
DEFAULT_APP_ENV = "development"
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
MIN_PORT = 1
MAX_PORT = 65535
SERVICE_UNAVAILABLE = 503
REDIS_TIMEOUT_SECONDS = 2
VISITS_KEY = "visits"

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{app_name}</title></head>
<body style="font-family: sans-serif; max-width: 40rem; margin: 3rem auto;">
  <h1>{app_name}</h1>
  <p>SWE40006 Deployment Portfolio - Task 4.3</p>
  <p>Visit number: <strong>{visits}</strong></p>
  <p>Environment: <strong>{app_env}</strong></p>
  <p>Served by container: <strong>{hostname}</strong></p>
</body>
</html>"""


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    redis_host: str
    redis_port: int


def parse_port(raw_value: str) -> int:
    if not raw_value.isdigit():
        raise ValueError(f"Port must be a number, got {raw_value!r}")
    port = int(raw_value)
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f"Port must be between {MIN_PORT} and {MAX_PORT}")
    return port


def load_settings() -> Settings:
    """Build settings from environment variables, falling back to defaults."""
    return Settings(
        app_name=os.environ.get("APP_NAME", DEFAULT_APP_NAME),
        app_env=os.environ.get("APP_ENV", DEFAULT_APP_ENV),
        redis_host=os.environ.get("REDIS_HOST", DEFAULT_REDIS_HOST),
        redis_port=parse_port(os.environ.get("REDIS_PORT", str(DEFAULT_REDIS_PORT))),
    )


def build_redis_client(settings: Settings) -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
        socket_timeout=REDIS_TIMEOUT_SECONDS,
    )


def create_app(
    settings: Settings | None = None, redis_client: redis.Redis | None = None
) -> FastAPI:
    settings = settings or load_settings()
    store = redis_client or build_redis_client(settings)
    application = FastAPI(title=settings.app_name)

    def redis_unavailable() -> JSONResponse:
        return JSONResponse(
            {"error": "Visit counter storage is unavailable"},
            status_code=SERVICE_UNAVAILABLE,
        )

    @application.get("/", response_class=HTMLResponse)
    def home():
        try:
            visits = store.incr(VISITS_KEY)
        except redis.RedisError:
            return HTMLResponse(
                "<h1>Service temporarily unavailable</h1>",
                status_code=SERVICE_UNAVAILABLE,
            )
        # Escape every value that comes from configuration or the system.
        return PAGE_TEMPLATE.format(
            app_name=html.escape(settings.app_name),
            app_env=html.escape(settings.app_env),
            visits=visits,
            hostname=html.escape(socket.gethostname()),
        )

    @application.get("/api/visits")
    def visits():
        try:
            count = int(store.get(VISITS_KEY) or 0)
        except redis.RedisError:
            return redis_unavailable()
        return {"visits": count}

    @application.get("/health")
    def health():
        try:
            store.ping()
        except redis.RedisError:
            return JSONResponse(
                {"status": "degraded", "redis": "down"},
                status_code=SERVICE_UNAVAILABLE,
            )
        return {"status": "ok", "redis": "up"}

    return application


def get_app() -> FastAPI:
    """Factory used by uvicorn: `uvicorn main:get_app --factory`."""
    return create_app()