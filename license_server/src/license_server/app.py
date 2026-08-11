from __future__ import annotations

import logging
import json
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .config import Settings
from .models import Base
from .routes import router
from .service import LicenseService


LOGGER = logging.getLogger("license_server")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def create_app(settings: Settings | None = None, *, create_schema: bool = False) -> FastAPI:
    configure_logging()
    configuration = settings or Settings.from_environment()
    engine = create_engine(configuration.database_url, pool_pre_ping=True)
    if create_schema:
        Base.metadata.create_all(engine)
    application = FastAPI(title="Copro Auto Licence", docs_url=None, redoc_url=None, openapi_url=None)
    application.state.database_engine = engine
    application.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    application.state.license_service = LicenseService(configuration)
    attempts: dict[str, deque[float]] = defaultdict(deque)

    @application.middleware("http")
    async def security_headers_and_rate_limit(request: Request, call_next):
        response = None
        if request.url.path == "/v1/activate":
            address = request.client.host if request.client else "unknown"
            now = time.monotonic()
            bucket = attempts[address]
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            if len(bucket) >= 20:
                response = JSONResponse(
                    {"detail": {"code": "rate_limited", "message": "Trop de tentatives."}}, status_code=429,
                )
            else:
                bucket.append(now)
        if response is None:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health")
    def health():
        try:
            with application.state.database_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            LOGGER.exception("database_health_check_failed")
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ok"}

    application.include_router(router)
    return application
