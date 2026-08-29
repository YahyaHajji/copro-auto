from datetime import date, time
from decimal import Decimal

import pytest

from copro_auto.documents.mappings import (
    format_elevation,
    format_french_datetime,
    format_level_elevation_range,
    format_level_heading,
    french_number,
    level_description,
    part_description,
)
from copro_auto.domain.models import Level, Part, PartNature, SurfaceBreakdown


def test_french_number_and_dossier_datetime_are_deterministic():
    assert french_number(2027) == "deux mille vingt-sept"
    assert format_french_datetime(date(2027, 8, 5), time(10, 0)) == (
        "L’an deux mille vingt-sept, le jeudi cinq août à dix heures."
    )
    assert format_french_datetime(date(2026, 1, 1), time(1, 30)).endswith(
        "à une heure trente."
    )


def test_elevations_always_have_a_sign_comma_and_two_decimals():
    assert format_elevation(Decimal("-2.2")) == "-2,20"
    assert format_elevation(Decimal("0")) == "+0,00"
    assert format_elevation(Decimal("3.8")) == "+3,80"


@pytest.mark.parametrize(
    ("starts", "ends", "expected"),
    [
        (("0.20",), ("3.10",), "de la cote +0,20 m à la cote +3,10 m"),
        (("0.20",), ("3.10", "5.70"), "de la cote +0,20 m aux cotes +3,10 m et +5,70 m"),
        (("0.00", "0.60"), ("3.60",), "des cotes +0,00 m et +0,60 m à la cote +3,60 m"),
        (
            ("-3.00", "-2.80"),
            ("-0.20", "0.40"),
            "des cotes -3,00 m et -2,80 m aux cotes -0,20 m et +0,40 m",
        ),
    ],
)
def test_level_elevation_range_supports_all_four_french_variants(starts, ends, expected):
    level = Level(
        "Niveau test",
        0,
        tuple(Decimal(value) for value in starts),
        tuple(Decimal(value) for value in ends),
    )

    assert format_level_elevation_range(level) == expected
    assert format_level_heading(level) == f"Niveau test : {expected}"


def test_multi_height_narrative_uses_plural_fixed_decimals():
    level = Level(
        "Rez-de-chaussée",
        0,
        (Decimal("0.20"),),
        (Decimal("3.10"), Decimal("5.70")),
        (Decimal("2.90"), Decimal("5.50")),
    )

    description = level_description(level)

    assert "de la cote +0,20 m aux cotes +3,10 m et +5,70 m" in description
    assert "de hauteurs intérieures de 2,90 m et 5,50 m" in description


def test_scalar_level_wording_remains_backward_compatible():
    level = Level(
        "Rez-de-chaussée",
        0,
        (Decimal("0.20"),),
        (Decimal("3.20"),),
        (Decimal("3.00"),),
    )

    assert format_level_heading(level) == (
        "Rez-de-chaussée : de la cote +0,20 m à la cote +3,20 m"
    )
    assert (
        "compris entre la cote +0,20 m et la cote +3,20 m, "
        "d’une hauteur intérieure de 3 m"
    ) in level_description(level)


def test_part_narrative_combines_short_consistency_surface_details_and_observation():
    part = Part(
        index="1",
        nature=PartNature.PRIVATE,
        consistency="Appartement",
        description="salon, cuisine, séjour et deux chambres",
        observations="Dont garage = 15 m²",
        surfaces=SurfaceBreakdown(inside_title=Decimal("81"), garage=Decimal("15")),
    )

    assert part_description(part) == (
        "PARTIE PRIVATIVE N° 1 : Appartement de 81 m², comprenant : "
        "salon, cuisine, séjour et deux chambres. Dont garage = 15 m²."
    )


def test_parenthetical_detail_is_appended_without_comprenant():
    part = Part(
        index="1A",
        nature=PartNature.PRIVATE,
        consistency="Escaliers vers sous-sol",
        description="(pour mémoire)",
        surfaces=SurfaceBreakdown(inside_title=Decimal("2")),
    )

    assert part_description(part) == (
        "PARTIE PRIVATIVE N° 1A : Escaliers vers sous-sol de 2 m² (pour mémoire)."
    )
