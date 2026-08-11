from __future__ import annotations

import hmac
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .admin_auth import (
    COOKIE_NAME,
    SESSION_SECONDS,
    AdminSession,
    address_digest,
    check_login,
    issue_session,
    verify_session,
)
from .admin_service import AdminError, AdminService


LOGGER = logging.getLogger("license_server.admin")
router = APIRouter(prefix="/admin")
STATIC_DIR = Path(__file__).with_name("static")


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class CreateLicenseRequest(BaseModel):
    organization: str = Field(min_length=2, max_length=200)
    plan: str
    seats: int = Field(ge=1, le=100)
    days: int = Field(ge=1, le=3650)
    trial: bool = False


class RenewRequest(BaseModel):
    days: int = Field(ge=1, le=3650)


def database(request: Request):
    with request.app.state.session_factory() as session:
        yield session


def admin_service(request: Request) -> AdminService:
    return request.app.state.admin_service


def current_session(request: Request) -> AdminSession | None:
    token = request.cookies.get(COOKIE_NAME, "")
    return verify_session(token, request.app.state.settings.admin_session_secret)


def require_admin(request: Request) -> AdminSession:
    claims = current_session(request)
    if claims is None:
        raise HTTPException(401, detail={"code": "unauthorized", "message": "Session administrateur requise."})
    return claims


def require_csrf(request: Request, claims: AdminSession = Depends(require_admin)) -> AdminSession:
    supplied = request.headers.get("X-CSRF-Token", "")
    if not supplied or not hmac.compare_digest(supplied, claims.csrf):
        raise HTTPException(403, detail={"code": "csrf", "message": "Requête de sécurité invalide."})
    return claims


def _address(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def _error(exc: AdminError) -> HTTPException:
    return HTTPException(exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.get("")
@router.get("/")
def dashboard():
    return FileResponse(STATIC_DIR / "admin.html", media_type="text/html")


@router.get("/api/session")
def session_status(request: Request):
    claims = current_session(request)
    return {"authenticated": claims is not None, "csrf": claims.csrf if claims else None}


@router.post("/api/login")
def login(payload: LoginRequest, request: Request, response: Response, session: Session = Depends(database)):
    settings = request.app.state.settings
    if not settings.admin_password_hash or not settings.admin_session_secret:
        raise HTTPException(503, detail={"code": "not_configured", "message": "Administration non configurée."})
    result = check_login(
        session,
        address_digest(_address(request), settings.key_pepper),
        payload.password,
        settings.admin_password_hash,
    )
    if result == "limited":
        LOGGER.warning("admin_login_rate_limited")
        raise HTTPException(429, detail={"code": "rate_limited", "message": "Trop de tentatives. Réessayez dans dix minutes."})
    if result == "invalid":
        LOGGER.warning("admin_login_failed")
        raise HTTPException(401, detail={"code": "invalid_credentials", "message": "Mot de passe incorrect."})
    token, claims = issue_session(settings.admin_session_secret)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        path="/admin",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    LOGGER.info("admin_login_succeeded")
    return {"authenticated": True, "csrf": claims.csrf}


@router.post("/api/logout")
def logout(response: Response, _claims: AdminSession = Depends(require_csrf)):
    response.delete_cookie(COOKIE_NAME, path="/admin", secure=True, httponly=True, samesite="strict")
    return {"ok": True}


@router.get("/api/summary")
def summary(
    session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_admin),
):
    return service.summary(session)


@router.get("/api/licenses")
def licenses(
    session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_admin),
):
    return {"items": service.list_licenses(session)}


@router.get("/api/licenses/{license_id}")
def license_detail(
    license_id: str, session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_admin),
):
    try:
        return service.get_license(session, license_id)
    except AdminError as exc:
        raise _error(exc) from exc


@router.post("/api/licenses")
def create_license(
    payload: CreateLicenseRequest, session: Session = Depends(database),
    service: AdminService = Depends(admin_service), _claims: AdminSession = Depends(require_csrf),
):
    try:
        result = service.create_license(
            session, payload.organization, payload.plan, payload.seats, payload.days, payload.trial,
        )
        LOGGER.info("admin_license_created license_id=%s", result["license_id"])
        return result
    except AdminError as exc:
        raise _error(exc) from exc


@router.post("/api/licenses/{license_id}/renew")
def renew_license(
    license_id: str, payload: RenewRequest, session: Session = Depends(database),
    service: AdminService = Depends(admin_service), _claims: AdminSession = Depends(require_csrf),
):
    try:
        result = service.renew(session, license_id, payload.days)
        LOGGER.info("admin_license_renewed license_id=%s", license_id)
        return result
    except AdminError as exc:
        raise _error(exc) from exc


@router.post("/api/licenses/{license_id}/revoke")
def revoke_license(
    license_id: str, session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_csrf),
):
    try:
        result = service.set_status(session, license_id, "revoked")
        LOGGER.info("admin_license_revoked license_id=%s", license_id)
        return result
    except AdminError as exc:
        raise _error(exc) from exc


@router.post("/api/licenses/{license_id}/reactivate")
def reactivate_license(
    license_id: str, session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_csrf),
):
    try:
        result = service.set_status(session, license_id, "active")
        LOGGER.info("admin_license_reactivated license_id=%s", license_id)
        return result
    except AdminError as exc:
        raise _error(exc) from exc


@router.post("/api/activations/{activation_id}/release")
def release_activation(
    activation_id: str, session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_csrf),
):
    try:
        result = service.release(session, activation_id)
        LOGGER.info("admin_activation_released activation_id=%s", activation_id)
        return result
    except AdminError as exc:
        raise _error(exc) from exc


@router.get("/api/audit")
def audit(
    session: Session = Depends(database), service: AdminService = Depends(admin_service),
    _claims: AdminSession = Depends(require_admin),
):
    return {"items": service.audit_events(session)}
