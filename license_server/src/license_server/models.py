from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="individual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    licenses: Mapped[list["License"]] = relationship(back_populates="organization")


class License(Base):
    __tablename__ = "licenses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    key_digest: Mapped[str] = mapped_column(String(64), unique=True)
    key_hint: Mapped[str] = mapped_column(String(12))
    plan: Mapped[str] = mapped_column(String(20), default="individual")
    status: Mapped[str] = mapped_column(String(20), default="active")
    seat_limit: Mapped[int] = mapped_column(Integer, default=2)
    trial: Mapped[bool] = mapped_column(Boolean, default=False)
    commercial_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    organization: Mapped[Organization] = relationship(back_populates="licenses")
    activations: Mapped[list["Activation"]] = relationship(back_populates="license")


class Activation(Base):
    __tablename__ = "activations"
    __table_args__ = (UniqueConstraint("license_id", "device_hash", name="uq_license_device"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    license_id: Mapped[str] = mapped_column(ForeignKey("licenses.id"), index=True)
    device_hash: Mapped[str] = mapped_column(String(64))
    device_label: Mapped[str] = mapped_column(String(160), default="")
    secret_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="active")
    app_version: Mapped[str] = mapped_column(String(30), default="")
    os_name: Mapped[str] = mapped_column(String(40), default="")
    os_edition: Mapped[str] = mapped_column(String(80), default="")
    os_version: Mapped[str] = mapped_column(String(80), default="")
    os_build: Mapped[str] = mapped_column(String(80), default="")
    architecture: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license: Mapped[License] = relationship(back_populates="activations")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    license_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    activation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ActivationAttempt(Base):
    __tablename__ = "activation_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    address_hash: Mapped[str] = mapped_column(String(64))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AdminLoginAttempt(Base):
    __tablename__ = "admin_login_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    address_hash: Mapped[str] = mapped_column(String(64))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


Index("ix_activation_license_status", Activation.license_id, Activation.status)
Index("ix_activation_attempt_address_time", ActivationAttempt.address_hash, ActivationAttempt.attempted_at)
Index("ix_admin_login_attempt_address_time", AdminLoginAttempt.address_hash, AdminLoginAttempt.attempted_at)
