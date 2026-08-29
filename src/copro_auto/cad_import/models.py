from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from copro_auto.domain.models import PartNature, SourceEvidence, decimal_tuple_from


class CadConfidence(StrEnum):
    HIGH = "élevée"
    MEDIUM = "moyenne"
    LOW = "faible"


@dataclass(slots=True)
class CadCandidate:
    field: str
    value: str
    confidence: CadConfidence
    evidence: SourceEvidence


@dataclass(slots=True)
class CadPartDraft:
    index: str
    nature: PartNature
    consistency: str = ""
    inside_title: Decimal = Decimal("0")
    overhang: Decimal = Decimal("0")
    observations: str = ""
    description_suggestion: str = ""
    accept_description_suggestion: bool = False
    description_confidence: CadConfidence = CadConfidence.LOW
    confidence: CadConfidence = CadConfidence.MEDIUM
    evidence: list[SourceEvidence] = field(default_factory=list)


@dataclass(slots=True)
class CadLevelDraft:
    name: str
    order: int
    start_elevations: tuple[Decimal, ...] = ()
    end_elevations: tuple[Decimal, ...] = ()
    interior_heights: tuple[Decimal, ...] = ()
    parts: list[CadPartDraft] = field(default_factory=list)
    confidence: CadConfidence = CadConfidence.MEDIUM
    elevation_ambiguous: bool = False
    evidence: list[SourceEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.start_elevations = decimal_tuple_from(self.start_elevations)
        self.end_elevations = decimal_tuple_from(self.end_elevations)
        self.interior_heights = decimal_tuple_from(self.interior_heights)


@dataclass(slots=True)
class CadImportDraft:
    source: Path
    fingerprint: str = ""
    size_bytes: int = 0
    values: dict[str, CadCandidate] = field(default_factory=dict)
    levels: list[CadLevelDraft] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    entity_counts: dict[str, int] = field(default_factory=dict)

    @property
    def part_count(self) -> int:
        return sum(len(level.parts) for level in self.levels)
