from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from copro_auto.domain.models import Level, Part, Project


def format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")


def format_elevation(value: Decimal) -> str:
    fixed = value.quantize(Decimal("0.01"))
    sign = "+" if fixed >= 0 else "-"
    return f"{sign}{abs(fixed):.2f}".replace(".", ",")


def format_height(value: Decimal) -> str:
    """Format a height with two decimal places and no elevation sign."""
    return f"{value.quantize(Decimal('0.01')):.2f}".replace(".", ",")


def _coordinate(values: tuple[Decimal, ...], formatter, *, suffix: str = "") -> str:
    rendered = [f"{formatter(value)}{suffix}" for value in values]
    if len(rendered) < 2:
        return "".join(rendered)
    if len(rendered) == 2:
        return " et ".join(rendered)
    return f"{', '.join(rendered[:-1])} et {rendered[-1]}"


def format_level_elevation_range(level: Level) -> str:
    """Return the signed cote range using the four French cardinality variants."""
    starts = level.start_elevations
    ends = level.end_elevations
    start_label = "de la cote" if len(starts) == 1 else "des cotes"
    start_values = _coordinate(starts, format_elevation, suffix=" m")
    if not ends:
        return f"{start_label} {start_values}"
    end_label = "à la cote" if len(ends) == 1 else "aux cotes"
    end_values = _coordinate(ends, format_elevation, suffix=" m")
    return f"{start_label} {start_values} {end_label} {end_values}"


def format_level_heading(level: Level) -> str:
    return f"{level.name} : {format_level_elevation_range(level)}"


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def format_month_year(value: date) -> str:
    months = (
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
    )
    return f"{months[value.month - 1]} {value.year}"


_SMALL_NUMBERS = (
    "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept",
    "dix-huit", "dix-neuf",
)


def _under_hundred(value: int) -> str:
    if value < 20:
        return _SMALL_NUMBERS[value]
    if value < 70:
        tens = ("", "", "vingt", "trente", "quarante", "cinquante", "soixante")
        ten, unit = divmod(value, 10)
        if unit == 0:
            return tens[ten]
        connector = " et " if unit == 1 else "-"
        return f"{tens[ten]}{connector}{_SMALL_NUMBERS[unit]}"
    if value < 80:
        remainder = value - 60
        connector = " et " if remainder == 11 else "-"
        return f"soixante{connector}{_SMALL_NUMBERS[remainder]}"
    remainder = value - 80
    if remainder == 0:
        return "quatre-vingts"
    return f"quatre-vingt-{_under_hundred(remainder)}"


def french_number(value: int) -> str:
    if not 0 <= value < 1_000_000:
        raise ValueError(f"Nombre français hors plage : {value}")
    if value < 100:
        return _under_hundred(value)
    if value < 1_000:
        hundreds, remainder = divmod(value, 100)
        prefix = "cent" if hundreds == 1 else f"{_SMALL_NUMBERS[hundreds]} cent"
        if remainder == 0:
            return prefix + ("s" if hundreds > 1 else "")
        return f"{prefix} {french_number(remainder)}"
    thousands, remainder = divmod(value, 1_000)
    prefix = "mille" if thousands == 1 else f"{french_number(thousands)} mille"
    if remainder == 0:
        return prefix
    return f"{prefix} {french_number(remainder)}"


def format_french_datetime(value: date, dossier_time: time) -> str:
    weekdays = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
    months = (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    )
    day = "premier" if value.day == 1 else french_number(value.day)
    hour = "une" if dossier_time.hour == 1 else french_number(dossier_time.hour)
    hour_label = "heure" if dossier_time.hour == 1 else "heures"
    minute_text = ""
    if dossier_time.minute == 1:
        minute_text = " et une minute"
    elif dossier_time.minute:
        minute_text = f" {french_number(dossier_time.minute)}"
    return (
        f"L’an {french_number(value.year)}, le {weekdays[value.weekday()]} {day} "
        f"{months[value.month - 1]} à {hour} {hour_label}{minute_text}."
    )


def client_sentence(project: Project) -> str:
    client = project.identity.client
    expiry = "" if client.national_id_expiry is None else format_date(client.national_id_expiry)
    return (
        f"M./Mme {client.full_name}, CNIE n° {client.national_id}, demeurant à {client.address}, "
        f"agissant en qualité de {client.capacity}, carte valable jusqu’au {expiry}."
    )


def level_name_with_article(name: str) -> str:
    stripped = name.strip()
    normalized = stripped.casefold().replace("’", "'")
    if normalized.startswith(("le ", "la ", "les ", "l'")):
        return stripped
    return f"Le {stripped}"


def level_description(level: Level) -> str:
    total = sum((part.surfaces.cadastral_total for part in level.parts), Decimal("0"))
    overhang = sum((part.surfaces.overhang for part in level.parts), Decimal("0"))
    private_count = sum(part.nature.value == "privative" for part in level.parts)
    common_count = len(level.parts) - private_count
    overhang_text = "" if not overhang else f", dont {format_decimal(overhang)} m² en surplomb"
    if not level.end_elevations:
        start_noun = "la cote" if len(level.start_elevations) == 1 else "les cotes"
        position = (
            f"situé à partir de {start_noun} "
            f"{_coordinate(level.start_elevations, format_elevation, suffix=' m')}"
        )
    elif len(level.start_elevations) == 1 and len(level.end_elevations) == 1:
        # Preserve the historical scalar wording for existing dossiers.
        position = (
            f"compris entre la cote {format_elevation(level.start_elevations[0])} m "
            f"et la cote {format_elevation(level.end_elevations[0])} m"
        )
    else:
        position = format_level_elevation_range(level)
    if not level.interior_heights:
        height = ""
    elif len(level.interior_heights) == 1:
        # Preserve the historical scalar rendering (for example ``3 m``).
        height = f", d’une hauteur intérieure de {format_decimal(level.interior_heights[0])} m"
    else:
        height = (
            ", de hauteurs intérieures de "
            f"{_coordinate(level.interior_heights, format_height, suffix=' m')}"
        )
    private_label = "partie privative" if private_count == 1 else "parties privatives"
    common_label = "partie commune" if common_count == 1 else "parties communes"
    division = (
        f"Il est divisé en {len(level.parts)} parties, dont {private_count} {private_label} "
        f"et {common_count} {common_label}, détaillées comme suit :"
    )
    display_name = level_name_with_article(level.name)
    return f"{display_name} couvrant une surface de {format_decimal(total)} m²{overhang_text}, {position}{height}. {division}"


def part_description(part: Part) -> str:
    nature = "PRIVATIVE" if part.nature.value == "privative" else "COMMUNE"
    consistency = part.consistency.strip().rstrip(".")
    total = format_decimal(part.surfaces.cadastral_total)
    overhang = "" if not part.surfaces.overhang else f", dont {format_decimal(part.surfaces.overhang)} m² en surplomb"
    narrative = f"PARTIE {nature} N° {part.index} : {consistency} de {total} m²{overhang}"
    detail = part.description.strip().rstrip(".")
    if detail:
        narrative += f" {detail}" if detail.startswith("(") else f", comprenant : {detail}"
    narrative += "."
    observation = part.observations.strip().rstrip(".")
    if observation:
        narrative += f" {observation}."
    return narrative


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
        "A.DAANOUNI": identity.surveyor,
        "A DAANOUNI": identity.surveyor,
        "Mr DAANOUNI ABDELAAZIZ": identity.surveyor,
        "20/10/2025": format_date(identity.project_date),
        "Octobre 2025": format_month_year(identity.project_date),
    }


def document_replacements(project: Project, kind: str) -> dict[str, str]:
    identity = project.identity
    if kind == "pv_division":
        return {
            "Meknès Al Ismaïlia": identity.land_registry_office,
            "Préfecture                : Meknès": f"Préfecture                : {identity.prefecture}",
            "Commune                : Meknès": f"Commune                : {identity.commune}",
            "L’an deux mille vingt-Cinq, le Lundi vingt Octobre à dix heures.": (
                format_french_datetime(identity.project_date, identity.project_time)
            ),
        }
    if kind == "reglement":
        return {
            "Préfecture de Meknès": f"Préfecture de {identity.prefecture}",
            "Commune de Meknès": f"Commune de {identity.commune}",
            "Fait à Meknès": f"Fait à {identity.commune or identity.prefecture}",
        }
    if kind in {"tableau_a", "tableau_b"}:
        return {"Meknès Al Ismaïlia": identity.prefecture}
    if kind == "tableau_recapitulatif":
        return {"Al Ismaïlia": identity.prefecture}
    return {}
