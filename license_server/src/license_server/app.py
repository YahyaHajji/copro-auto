from __future__ import annotations

import logging
import json
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .models import ActivationAttempt, Base
from .routes import router
from .service import LicenseService


LOGGER = logging.getLogger("license_server")


def _consume_activation_attempt(session_factory, address_hash: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    with session_factory() as session:
        session.execute(delete(ActivationAttempt).where(ActivationAttempt.attempted_at < cutoff))
        attempt_count = session.scalar(
            select(func.count()).select_from(ActivationAttempt).where(
                ActivationAttempt.address_hash == address_hash,
                ActivationAttempt.attempted_at >= cutoff,
            ),
        ) or 0
        if attempt_count >= 20:
            session.commit()
            return False
        session.add(ActivationAttempt(address_hash=address_hash))
        session.commit()
        return True


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
    @application.middleware("http")
    async def security_headers_and_rate_limit(request: Request, call_next):
        response = None
        if request.url.path == "/v1/activate":
            address = request.client.host if request.client else "unknown"
            address_hash = hmac.new(
                configuration.key_pepper.encode("utf-8"),
                address.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            allowed = await run_in_threadpool(
                _consume_activation_attempt,
                application.state.session_factory,
                address_hash,
            )
            if not allowed:
                LOGGER.warning("activation_rate_limited")
                response = JSONResponse(
                    {"detail": {"code": "rate_limited", "message": "Trop de tentatives."}}, status_code=429,
                )
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
