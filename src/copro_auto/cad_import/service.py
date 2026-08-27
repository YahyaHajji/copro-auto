from __future__ import annotations

import hashlib
import shutil
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from copro_auto.domain.models import (
    EvidenceSource,
    FieldDecision,
    Level,
    Part,
    Project,
    SourceEvidence,
    SurfaceBreakdown,
)

from .dxf_parser import CadImportResult, parse_dxf
from .dwg_converter import convert_dwg_to_dxf
from .models import CadCandidate, CadImportDraft, CadLevelDraft


@dataclass(frozen=True, slots=True)
class Comparison:
    field: str
    manual_value: str | None
    cad_value: str | None
    status: str
    candidate: CadCandidate | None = None


def _retarget_provenance(result: CadImportDraft, source: Path, fingerprint: str, size_bytes: int) -> None:
    result.source = source
    result.fingerprint = fingerprint
    result.size_bytes = size_bytes
    for candidate in result.values.values():
        candidate.evidence.source_file = str(source)
    for level in result.levels:
        for evidence in level.evidence:
            evidence.source_file = str(source)
        for part in level.parts:
            for evidence in part.evidence:
                evidence.source_file = str(source)


def import_cad(path: str | Path) -> CadImportDraft:
    source = Path(path).resolve(strict=True)
    extension = source.suffix.casefold()
    if extension == ".dxf":
        return parse_dxf(source)
    if extension != ".dwg":
        raise ValueError("Sélectionnez un fichier DWG ou DXF.")

    raw = source.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    converted: Path | None = None
    try:
        converted = convert_dwg_to_dxf(source)
        result = parse_dxf(converted)
        _retarget_provenance(result, source, fingerprint, len(raw))
        return result
    finally:
        if converted is not None:
            shutil.rmtree(converted.parent, ignore_errors=True)


def project_fields(project: Project) -> dict[str, str]:
    identity = project.identity
    return {
        "identity.land_title": identity.land_title,
        "identity.property_name": identity.property_name,
        "identity.prefecture": identity.prefecture,
        "identity.commune": identity.commune,
        "identity.subdivision": identity.subdivision,
    }


def compare(project: Project, result: CadImportDraft) -> list[Comparison]:
    manual = project_fields(project)
    fields = sorted(set(manual) | set(result.values))
    comparisons: list[Comparison] = []
    for field_name in fields:
        manual_value = manual.get(field_name) or None
        candidate = result.values.get(field_name)
        cad_value = candidate.value if candidate else None
        status = "identique" if manual_value and cad_value and manual_value.casefold() == cad_value.casefold() else "différent"
        if manual_value is None or cad_value is None:
            status = "manquant"
        comparisons.append(Comparison(field_name, manual_value, cad_value, status, candidate))
    return comparisons


def _record_decision(project: Project, comparison: Comparison, value: str, choose_cad: bool, fingerprint: str = "") -> None:
    candidate = comparison.candidate
    project.decisions.append(FieldDecision(
        field_path=comparison.field,
        manual_value=comparison.manual_value,
        cad_value=comparison.cad_value,
        active_value=value,
        selected_source=EvidenceSource.DXF_TEXT if choose_cad else EvidenceSource.MANUAL,
        confidence=candidate.confidence.value if choose_cad and candidate else "",
        source_file=candidate.evidence.source_file if choose_cad and candidate else "",
        entity_reference=candidate.evidence.entity_reference if choose_cad and candidate else "",
        source_fingerprint=fingerprint if choose_cad else "",
    ))


def apply_choice(project: Project, comparison: Comparison, choose_cad: bool, fingerprint: str = "") -> None:
    value = comparison.cad_value if choose_cad else comparison.manual_value
    if value is None:
        raise ValueError("La source choisie ne contient aucune valeur.")
    target, attribute = comparison.field.split(".", 1)
    if target != "identity" or not hasattr(project.identity, attribute):
        raise ValueError(f"Champ de réconciliation non pris en charge : {comparison.field}")
    setattr(project.identity, attribute, value)
    _record_decision(project, comparison, value, choose_cad, fingerprint)


def project_is_empty(project: Project) -> bool:
    identity = project.identity
    return not project.levels and not any((
        identity.land_title.strip(), identity.property_name.strip(), identity.prefecture.strip(),
        identity.commune.strip(), identity.subdivision.strip(), identity.surveyor.strip(),
    ))


def _source_evidence(level: CadLevelDraft, draft: CadImportDraft) -> SourceEvidence:
    if level.evidence:
        return deepcopy(level.evidence[0])
    return SourceEvidence(
        source=EvidenceSource.DXF_TABLE,
        raw_value=level.name,
        source_file=str(draft.source),
        entity_reference="",
    )


def _levels_from_draft(draft: CadImportDraft) -> list[Level]:
    levels: list[Level] = []
    for order, level in enumerate(draft.levels):
        evidence = _source_evidence(level, draft)
        parts = [Part(
            index=part.index,
            nature=part.nature,
            consistency=part.consistency,
            description=part.description_suggestion if part.accept_description_suggestion else "",
            observations=part.observations,
            surfaces=SurfaceBreakdown(
                inside_title=part.inside_title,
                overhang=part.overhang,
                excluding_balcony=part.inside_title + part.overhang,
            ),
            evidence=deepcopy(part.evidence) or [deepcopy(evidence)],
        ) for part in level.parts]
        levels.append(Level(
            name=level.name,
            order=order,
            start_elevations=level.start_elevations,
            end_elevations=level.end_elevations,
            interior_heights=level.interior_heights,
            parts=parts,
        ))
    return levels


def apply_reviewed_draft(
    project: Project,
    draft: CadImportDraft,
    selected_identity: dict[str, str],
    *,
    replace_levels: bool,
) -> Project:
    """Return a fully reconciled copy; the supplied project is never mutated."""
    candidate_project = deepcopy(project)
    comparisons = {item.field: item for item in compare(project, draft)}
    for field_name, value in selected_identity.items():
        comparison = comparisons.get(field_name)
        if comparison is None:
            continue
        if not value and comparison.manual_value is None and comparison.cad_value is None:
            continue
        choose_cad = comparison.cad_value is not None and value == comparison.cad_value
        target, attribute = field_name.split(".", 1)
        if target != "identity" or not hasattr(candidate_project.identity, attribute):
            continue
        setattr(candidate_project.identity, attribute, value)
        _record_decision(candidate_project, comparison, value, choose_cad, draft.fingerprint)

    if replace_levels:
        candidate_project.levels = _levels_from_draft(draft)
        confidences = {level.confidence.value for level in draft.levels}
        confidence = (
            "faible" if "faible" in confidences
            else "moyenne" if "moyenne" in confidences
            else "élevée" if confidences else ""
        )
        candidate_project.decisions.append(FieldDecision(
            field_path="levels",
            manual_value=str(len(project.levels)),
            cad_value=str(len(draft.levels)),
            active_value=str(len(candidate_project.levels)),
            selected_source=EvidenceSource.DXF_TABLE,
            confidence=confidence,
            source_file=str(draft.source),
            source_fingerprint=draft.fingerprint,
        ))
    return candidate_project
