from __future__ import annotations

from datetime import date
from decimal import Decimal

from copro_auto.domain.models import Level, Part, Project


def format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def format_month_year(value: date) -> str:
    months = (
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
    )
    return f"{months[value.month - 1]} {value.year}"


def level_description(level: Level) -> str:
    total = sum((part.surfaces.cadastral_total for part in level.parts), Decimal("0"))
    overhang = sum((part.surfaces.overhang for part in level.parts), Decimal("0"))
    private_count = sum(part.nature.value == "privative" for part in level.parts)
    common_count = len(level.parts) - private_count
    overhang_text = "" if not overhang else f", dont {format_decimal(overhang)} m² en surplomb"
    if level.end_elevation is None:
        position = f"situé à partir de la cote +{format_decimal(level.start_elevation)} m"
    else:
        position = (
            f"compris entre la cote +{format_decimal(level.start_elevation)} m "
            f"et la cote +{format_decimal(level.end_elevation)} m"
        )
    height = "" if level.interior_height is None else f", d’une hauteur intérieure de {format_decimal(level.interior_height)} m"
    private_label = "partie privative" if private_count == 1 else "parties privatives"
    common_label = "partie commune" if common_count == 1 else "parties communes"
    division = (
        f"Il est divisé en {len(level.parts)} parties, dont {private_count} {private_label} "
        f"et {common_count} {common_label}, détaillées comme suit :"
    )
    return f"Le {level.name} couvrant une surface de {format_decimal(total)} m²{overhang_text}, {position}{height}. {division}"


def part_description(part: Part) -> str:
    nature = "PRIVATIVE" if part.nature.value == "privative" else "COMMUNE"
    if part.description.strip():
        return f"PARTIE {nature} N° {part.index} : {part.description.strip()}"
    total = format_decimal(part.surfaces.cadastral_total)
    overhang = "" if not part.surfaces.overhang else f", dont {format_decimal(part.surfaces.overhang)} m² en surplomb"
    observation = "" if not part.observations else f" {part.observations}."
    return f"PARTIE {nature} N° {part.index} : {part.consistency} de {total} m²{overhang}.{observation}".replace("..", ".")


def base_replacements(project: Project) -> dict[str, str]:
    identity = project.identity
    return {
        "Yasmine  27": identity.property_name,
        "Yasmine 27": identity.property_name,
        "81819/38": identity.land_title,
        "119753/59": identity.land_title,
        "YASMIN 71": identity.property_name.upper(),
        "Yasmin 71": identity.property_name,
        "Yasmin": identity.subdivision or identity.property_name,
        "Meknès": identity.commune or identity.prefecture,
        "A.DAANOUNI": identity.surveyor,
        "A DAANOUNI": identity.surveyor,
        "20/10/2025": format_date(identity.project_date),
        "Octobre 2025": format_month_year(identity.project_date),
    }
