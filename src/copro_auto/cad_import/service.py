from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from copro_auto.domain.models import EvidenceSource, FieldDecision, Project

from .dxf_parser import CadImportResult, parse_dxf
from .dwg_converter import convert_dwg_to_dxf


@dataclass(frozen=True, slots=True)
class Comparison:
    field: str
    manual_value: str | None
    cad_value: str | None
    status: str


def import_cad(path: str | Path) -> CadImportResult:
    source = Path(path)
    if source.suffix.casefold() == ".dwg":
        return parse_dxf(convert_dwg_to_dxf(source))
    if source.suffix.casefold() == ".dxf":
        return parse_dxf(source)
    raise ValueError("Sélectionnez un fichier DWG ou DXF.")


def project_fields(project: Project) -> dict[str, str]:
    identity = project.identity
    return {
        "identity.land_title": identity.land_title,
        "identity.property_name": identity.property_name,
        "identity.prefecture": identity.prefecture,
        "identity.subdivision": identity.subdivision,
    }


def compare(project: Project, result: CadImportResult) -> list[Comparison]:
    manual = project_fields(project)
    fields = sorted(set(manual) | set(result.values))
    comparisons: list[Comparison] = []
    for field_name in fields:
        manual_value = manual.get(field_name) or None
        cad_value = result.values.get(field_name).value if field_name in result.values else None
        status = "identique" if manual_value and cad_value and manual_value.casefold() == cad_value.casefold() else "différent"
        if manual_value is None or cad_value is None:
            status = "manquant"
        comparisons.append(Comparison(field_name, manual_value, cad_value, status))
    return comparisons


def apply_choice(project: Project, comparison: Comparison, choose_cad: bool) -> None:
    value = comparison.cad_value if choose_cad else comparison.manual_value
    if value is None:
        raise ValueError("La source choisie ne contient aucune valeur.")
    target, attribute = comparison.field.split(".", 1)
    if target != "identity" or not hasattr(project.identity, attribute):
        raise ValueError(f"Champ de réconciliation non pris en charge : {comparison.field}")
    setattr(project.identity, attribute, value)
    project.decisions.append(FieldDecision(
        field_path=comparison.field,
        manual_value=comparison.manual_value,
        cad_value=comparison.cad_value,
        active_value=value,
        selected_source=EvidenceSource.DXF_TEXT if choose_cad else EvidenceSource.MANUAL,
    ))

