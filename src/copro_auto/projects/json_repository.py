from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from copro_auto.domain.models import (
    EvidenceSource,
    FieldDecision,
    GenerationRecord,
    Level,
    Part,
    PartNature,
    Project,
    ProjectIdentity,
    SourceEvidence,
    SurfaceBreakdown,
    decimal_from,
)


CURRENT_SCHEMA_VERSION = 1


class ProjectFormatError(ValueError):
    pass


def _surface_to_dict(value: SurfaceBreakdown) -> dict[str, str]:
    return {
        "inside_title": str(value.inside_title),
        "overhang": str(value.overhang),
        "excluding_balcony": str(value.excluding_balcony),
        "balcony": str(value.balcony),
        "courtyard": str(value.courtyard),
        "terrace": str(value.terrace),
        "garage": str(value.garage),
    }


def project_to_dict(project: Project) -> dict[str, Any]:
    identity = project.identity
    return {
        "schema_version": project.schema_version,
        "id": project.id,
        "created_at": project.created_at,
        "modified_at": project.modified_at,
        "identity": {
            "land_title": identity.land_title,
            "property_name": identity.property_name,
            "prefecture": identity.prefecture,
            "commune": identity.commune,
            "subdivision": identity.subdivision,
            "surveyor": identity.surveyor,
            "project_date": identity.project_date.isoformat(),
            "land_area": str(identity.land_area),
            "overall_consistency": identity.overall_consistency,
            "total_height": str(identity.total_height),
            "boundaries": identity.boundaries,
        },
        "levels": [
            {
                "id": level.id,
                "name": level.name,
                "order": level.order,
                "start_elevation": str(level.start_elevation),
                "end_elevation": None if level.end_elevation is None else str(level.end_elevation),
                "interior_height": None if level.interior_height is None else str(level.interior_height),
                "parts": [
                    {
                        "id": part.id,
                        "index": part.index,
                        "nature": part.nature.value,
                        "consistency": part.consistency,
                        "observations": part.observations,
                        "description": part.description,
                        "surfaces": _surface_to_dict(part.surfaces),
                        "evidence": [
                            {
                                "source": evidence.source.value,
                                "raw_value": evidence.raw_value,
                                "source_file": evidence.source_file,
                                "entity_reference": evidence.entity_reference,
                            }
                            for evidence in part.evidence
                        ],
                    }
                    for part in level.parts
                ],
            }
            for level in project.levels
        ],
        "decisions": [
            {
                "field_path": decision.field_path,
                "manual_value": decision.manual_value,
                "cad_value": decision.cad_value,
                "active_value": decision.active_value,
                "selected_source": decision.selected_source.value,
                "decided_at": decision.decided_at,
            }
            for decision in project.decisions
        ],
        "generations": [
            {
                "generated_at": record.generated_at,
                "app_version": record.app_version,
                "template_hashes": record.template_hashes,
                "files": record.files,
                "validation_ok": record.validation_ok,
            }
            for record in project.generations
        ],
    }


def _surface_from_dict(data: dict[str, Any]) -> SurfaceBreakdown:
    return SurfaceBreakdown(**{key: decimal_from(data.get(key, "0")) for key in (
        "inside_title", "overhang", "excluding_balcony", "balcony", "courtyard", "terrace", "garage"
    )})


def project_from_dict(data: dict[str, Any]) -> Project:
    version = data.get("schema_version")
    if version != CURRENT_SCHEMA_VERSION:
        raise ProjectFormatError(f"Version de projet non prise en charge : {version!r}.")
    try:
        identity_data = data["identity"]
        identity = ProjectIdentity(
            land_title=str(identity_data["land_title"]),
            property_name=str(identity_data["property_name"]),
            prefecture=str(identity_data.get("prefecture", "")),
            commune=str(identity_data.get("commune", "")),
            subdivision=str(identity_data.get("subdivision", "")),
            surveyor=str(identity_data.get("surveyor", "")),
            project_date=date.fromisoformat(identity_data.get("project_date", date.today().isoformat())),
            land_area=decimal_from(identity_data.get("land_area")),
            overall_consistency=str(identity_data.get("overall_consistency", "")),
            total_height=decimal_from(identity_data.get("total_height")),
            boundaries=dict(identity_data.get("boundaries", {})),
        )
        levels: list[Level] = []
        for level_data in data.get("levels", []):
            parts: list[Part] = []
            for part_data in level_data.get("parts", []):
                evidence = [
                    SourceEvidence(
                        source=EvidenceSource(item["source"]),
                        raw_value=str(item.get("raw_value", "")),
                        source_file=str(item.get("source_file", "")),
                        entity_reference=str(item.get("entity_reference", "")),
                    )
                    for item in part_data.get("evidence", [])
                ]
                parts.append(Part(
                    id=str(part_data["id"]),
                    index=str(part_data["index"]),
                    nature=PartNature(part_data["nature"]),
                    consistency=str(part_data["consistency"]),
                    observations=str(part_data.get("observations", "")),
                    description=str(part_data.get("description", "")),
                    surfaces=_surface_from_dict(part_data.get("surfaces", {})),
                    evidence=evidence,
                ))
            levels.append(Level(
                id=str(level_data["id"]),
                name=str(level_data["name"]),
                order=int(level_data["order"]),
                start_elevation=decimal_from(level_data["start_elevation"]),
                end_elevation=None if level_data.get("end_elevation") is None else decimal_from(level_data["end_elevation"]),
                interior_height=None if level_data.get("interior_height") is None else decimal_from(level_data["interior_height"]),
                parts=parts,
            ))
        decisions = [FieldDecision(
            field_path=str(item["field_path"]),
            manual_value=item.get("manual_value"),
            cad_value=item.get("cad_value"),
            active_value=str(item["active_value"]),
            selected_source=EvidenceSource(item["selected_source"]),
            decided_at=str(item["decided_at"]),
        ) for item in data.get("decisions", [])]
        generations = [GenerationRecord(**item) for item in data.get("generations", [])]
        return Project(
            schema_version=version,
            id=str(data["id"]),
            created_at=str(data["created_at"]),
            modified_at=str(data["modified_at"]),
            identity=identity,
            levels=levels,
            decisions=decisions,
            generations=generations,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectFormatError(f"Projet JSON invalide : {exc}") from exc


class JsonProjectRepository:
    def load(self, path: str | Path) -> Project:
        source = Path(path)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectFormatError(f"Impossible de lire le projet : {exc}") from exc
        if not isinstance(data, dict):
            raise ProjectFormatError("La racine du projet JSON doit être un objet.")
        return project_from_dict(data)

    def save(self, project: Project, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        project.modified_at = datetime.now(timezone.utc).isoformat()
        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
        content = json.dumps(project_to_dict(project), ensure_ascii=False, indent=2)
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        return destination
