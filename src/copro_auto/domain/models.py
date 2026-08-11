from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4


ZERO = Decimal("0")


class PartNature(StrEnum):
    PRIVATE = "privative"
    COMMON = "commune"


class EvidenceSource(StrEnum):
    MANUAL = "manual"
    DXF_TABLE = "dxf_table"
    DXF_TEXT = "dxf_text"


@dataclass(slots=True)
class SurfaceBreakdown:
    inside_title: Decimal = ZERO
    overhang: Decimal = ZERO
    excluding_balcony: Decimal = ZERO
    balcony: Decimal = ZERO
    courtyard: Decimal = ZERO
    terrace: Decimal = ZERO
    garage: Decimal = ZERO

    @property
    def cadastral_total(self) -> Decimal:
        return self.inside_title + self.overhang

    @property
    def architectural_total(self) -> Decimal:
        if self.excluding_balcony or self.balcony:
            return self.excluding_balcony + self.balcony
        return self.cadastral_total


@dataclass(slots=True)
class SourceEvidence:
    source: EvidenceSource
    raw_value: str
    source_file: str = ""
    entity_reference: str = ""


@dataclass(slots=True)
class FieldDecision:
    field_path: str
    manual_value: str | None
    cad_value: str | None
    active_value: str
    selected_source: EvidenceSource
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class Part:
    index: str
    nature: PartNature
    consistency: str
    surfaces: SurfaceBreakdown
    observations: str = ""
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    evidence: list[SourceEvidence] = field(default_factory=list)


@dataclass(slots=True)
class Level:
    name: str
    order: int
    start_elevation: Decimal
    end_elevation: Decimal | None
    interior_height: Decimal | None
    parts: list[Part] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class ProjectIdentity:
    land_title: str
    property_name: str
    prefecture: str = ""
    commune: str = ""
    subdivision: str = ""
    surveyor: str = ""
    project_date: date = field(default_factory=date.today)
    land_area: Decimal = ZERO
    overall_consistency: str = ""
    total_height: Decimal = ZERO
    boundaries: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationRecord:
    generated_at: str
    app_version: str
    template_hashes: dict[str, str]
    files: list[str]
    validation_ok: bool


@dataclass(slots=True)
class Project:
    identity: ProjectIdentity
    levels: list[Level] = field(default_factory=list)
    decisions: list[FieldDecision] = field(default_factory=list)
    generations: list[GenerationRecord] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def decimal_from(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or "0"))
