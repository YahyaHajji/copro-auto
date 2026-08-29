from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4


ZERO = Decimal("0")


def decimal_from(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or "0"))


def decimal_tuple_from(values: Any) -> tuple[Decimal, ...]:
    """Normalize one or more decimal values while preserving their order."""
    if values is None:
        return ()
    if isinstance(values, (str, Decimal, int, float)):
        source = (values,)
    else:
        source = tuple(values)
    result: list[Decimal] = []
    for value in source:
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        parsed = decimal_from(value)
        if parsed not in result:
            result.append(parsed)
    return tuple(result)


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
    confidence: str = ""
    source_file: str = ""
    entity_reference: str = ""
    source_fingerprint: str = ""
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
    start_elevations: tuple[Decimal, ...]
    end_elevations: tuple[Decimal, ...] = ()
    interior_heights: tuple[Decimal, ...] = ()
    parts: list[Part] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        self.start_elevations = decimal_tuple_from(self.start_elevations)
        self.end_elevations = decimal_tuple_from(self.end_elevations)
        self.interior_heights = decimal_tuple_from(self.interior_heights)

    @property
    def start_elevation(self) -> Decimal:
        """Compatibility view used until CAD and documents adopt plural values."""
        return self.start_elevations[0] if self.start_elevations else ZERO

    @start_elevation.setter
    def start_elevation(self, value: Decimal) -> None:
        self.start_elevations = decimal_tuple_from(value)

    @property
    def end_elevation(self) -> Decimal | None:
        return max(self.end_elevations) if self.end_elevations else None

    @end_elevation.setter
    def end_elevation(self, value: Decimal | None) -> None:
        self.end_elevations = decimal_tuple_from(value)

    @property
    def interior_height(self) -> Decimal | None:
        return self.interior_heights[0] if len(self.interior_heights) == 1 else None

    @interior_height.setter
    def interior_height(self, value: Decimal | None) -> None:
        self.interior_heights = decimal_tuple_from(value)


@dataclass(slots=True)
class ClientInformation:
    full_name: str = ""
    national_id: str = ""
    address: str = ""
    capacity: str = ""
    national_id_expiry: date | None = None


@dataclass(slots=True)
class ProjectIdentity:
    land_title: str
    property_name: str
    prefecture: str = ""
    commune: str = ""
    subdivision: str = ""
    surveyor: str = ""
    project_date: date = field(default_factory=date.today)
    project_time: time = field(default_factory=lambda: time(10, 0))
    land_area: Decimal = ZERO
    overall_consistency: str = ""
    total_height: Decimal = ZERO
    land_registry_office: str = ""
    client: ClientInformation = field(default_factory=ClientInformation)
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
    schema_version: int = 4
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
