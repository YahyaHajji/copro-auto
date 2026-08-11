from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .service import LicenseService, ServiceError


router = APIRouter(prefix="/v1")


class ActivateRequest(BaseModel):
    license_key: str = Field(min_length=12, max_length=100)
    device_hash: str = Field(min_length=64, max_length=64)
    device_label: str = Field(default="", max_length=160)
    app_version: str = Field(default="", max_length=30)


class ActivationRequest(BaseModel):
    activation_id: str
    activation_secret: str = Field(min_length=20, max_length=200)


class RefreshRequest(ActivationRequest):
    device_hash: str = Field(min_length=64, max_length=64)
    app_version: str = Field(default="", max_length=30)


def session(request: Request):
    with request.app.state.session_factory() as database:
        yield database


def service(request: Request) -> LicenseService:
    return request.app.state.license_service


def handle(exc: ServiceError) -> HTTPException:
    return HTTPException(exc.status_code, detail={"code": exc.code, "message": exc.message})


@router.post("/activate")
def activate(payload: ActivateRequest, database: Session = Depends(session), licenses: LicenseService = Depends(service)):
    try:
        token, secret = licenses.activate(
            database, payload.license_key, payload.device_hash, payload.device_label, payload.app_version,
        )
        return {"token": token, "activation_secret": secret}
    except ServiceError as exc:
        raise handle(exc) from exc


@router.post("/refresh")
def refresh(payload: RefreshRequest, database: Session = Depends(session), licenses: LicenseService = Depends(service)):
    try:
        token = licenses.refresh(
            database, payload.activation_id, payload.activation_secret, payload.device_hash, payload.app_version,
        )
        return {"token": token}
    except ServiceError as exc:
        raise handle(exc) from exc


@router.post("/deactivate")
def deactivate(payload: ActivationRequest, database: Session = Depends(session), licenses: LicenseService = Depends(service)):
    try:
        licenses.deactivate(database, payload.activation_id, payload.activation_secret)
        return {"ok": True}
    except ServiceError as exc:
        raise handle(exc) from exc


@router.post("/status")
def status(payload: ActivationRequest, database: Session = Depends(session), licenses: LicenseService = Depends(service)):
    try:
        return licenses.status(database, payload.activation_id, payload.activation_secret)
    except ServiceError as exc:
        raise handle(exc) from exc
