from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal
from enum import StrEnum

from .calculations import calculate_shares
from .models import PartNature, Project


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: Severity
    field: str
    message: str


def validate_project(project: Project) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    identity = project.identity
    if not identity.land_title.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.land_title", "Le titre foncier est obligatoire."))
    if not identity.property_name.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.property_name", "La propriété dite est obligatoire."))
    if identity.land_area <= 0:
        issues.append(ValidationIssue(Severity.ERROR, "identity.land_area", "La superficie du terrain doit être positive."))
    if not identity.prefecture.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.prefecture", "La préfecture est obligatoire."))
    if not identity.commune.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.commune", "La commune est obligatoire."))
    if not identity.subdivision.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.subdivision", "Le lotissement ou secteur est obligatoire."))
    if not identity.surveyor.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.surveyor", "Le nom du topographe est obligatoire."))
    if not identity.overall_consistency.strip():
        issues.append(ValidationIssue(Severity.ERROR, "identity.overall_consistency", "La consistance générale est obligatoire."))
    if identity.total_height <= 0:
        issues.append(ValidationIssue(Severity.ERROR, "identity.total_height", "La hauteur totale doit être positive."))
    if not project.levels:
        issues.append(ValidationIssue(Severity.ERROR, "levels", "Ajoutez au moins un niveau."))

    private_indices: set[str] = set()
    private_count = 0
    for level in project.levels:
        prefix = f"levels.{level.id}"
        level_indices: set[str] = set()
        if level.end_elevation is not None and level.end_elevation <= level.start_elevation:
            issues.append(ValidationIssue(Severity.ERROR, f"{prefix}.end_elevation", "La cote de fin doit dépasser la cote de début."))
        if not level.parts:
            issues.append(ValidationIssue(Severity.WARNING, f"{prefix}.parts", f"Le niveau « {level.name} » ne contient aucune partie."))
        for part in level.parts:
            part_path = f"{prefix}.parts.{part.id}"
            normalized_index = part.index.strip().casefold()
            if not normalized_index:
                issues.append(ValidationIssue(Severity.ERROR, f"{part_path}.index", "L'indice de partie est obligatoire."))
            elif normalized_index in level_indices or (
                part.nature is PartNature.PRIVATE and normalized_index in private_indices
            ):
                issues.append(ValidationIssue(Severity.ERROR, f"{part_path}.index", f"L'indice « {part.index} » est dupliqué."))
            else:
                level_indices.add(normalized_index)
                if part.nature is PartNature.PRIVATE:
                    private_indices.add(normalized_index)
            if not part.consistency.strip():
                issues.append(ValidationIssue(Severity.ERROR, f"{part_path}.consistency", "La consistance est obligatoire."))
            if not part.description.strip():
                issues.append(ValidationIssue(Severity.WARNING, f"{part_path}.description", "Ajoutez une description détaillée pour les documents narratifs."))
            values = [getattr(part.surfaces, item.name) for item in fields(part.surfaces)]
            if any(value < 0 for value in values):
                issues.append(ValidationIssue(Severity.ERROR, f"{part_path}.surfaces", "Les surfaces ne peuvent pas être négatives."))
            if part.nature is PartNature.PRIVATE:
                private_count += 1
                if part.surfaces.cadastral_total <= 0:
                    issues.append(ValidationIssue(Severity.ERROR, f"{part_path}.surfaces", "Une partie privative doit avoir une surface positive."))
            cadastral = part.surfaces.cadastral_total
            architectural = part.surfaces.architectural_total
            if (part.surfaces.excluding_balcony or part.surfaces.balcony) and cadastral != architectural:
                issues.append(ValidationIssue(Severity.WARNING, f"{part_path}.surfaces", f"Les décompositions cadastrale ({cadastral}) et architecturale ({architectural}) diffèrent."))
            if part.surfaces.overhang > 0 and not part.observations.strip():
                issues.append(ValidationIssue(Severity.WARNING, f"{part_path}.observations", "Ajoutez une observation pour le surplomb."))

    if private_count == 0:
        issues.append(ValidationIssue(Severity.ERROR, "levels.parts", "Ajoutez au moins une partie privative."))
    elif not any(issue.severity is Severity.ERROR for issue in issues):
        shares = calculate_shares(project)
        if sum(item.ten_thousandths for item in shares) != 10_000:
            issues.append(ValidationIssue(Severity.ERROR, "shares", "La somme des tantièmes doit être égale à 10 000."))
        if sum((item.percentage for item in shares), Decimal("0")) != Decimal("100.00"):
            issues.append(ValidationIssue(Severity.ERROR, "shares", "La somme des quotes-parts doit être égale à 100,00 %."))
    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)
