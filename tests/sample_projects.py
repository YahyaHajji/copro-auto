from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from copro_auto.domain.models import ClientInformation, Level, Part, PartNature, Project, ProjectIdentity, SurfaceBreakdown


def build_yasmin_project() -> Project:
    identity = ProjectIdentity(
        land_title="119753/59",
        property_name="YASMIN 71",
        prefecture="Meknès",
        commune="Meknès",
        subdivision="Yasmin",
        surveyor="A. DAANOUNI",
        project_date=date(2025, 10, 20),
        project_time=time(10, 0),
        land_area=Decimal("100"),
        overall_consistency="RDC + 2 Étages + Terrasse",
        total_height=Decimal("9.80"),
        land_registry_office="Meknès Al Ismaïlia",
        client=ClientInformation(
            full_name="Karim El Mansouri",
            national_id="AB123456",
            address="12 rue Yasmin, Meknès",
            capacity="propriétaire",
            national_id_expiry=date(2029, 7, 22),
        ),
        boundaries={
            "northeast": "T.119761/59 T.N et T.119762/59 T.N",
            "northwest": "T.119754/59 RDC+2 étages",
            "southeast": "T.119752/59 en cours de construction",
            "southwest": "Rue de lotissement de 12 m",
        },
    )
    return Project(identity=identity, levels=[
        Level("Rez-de-chaussée", 0, (Decimal("0.20"),), (Decimal("3.20"),), (Decimal("3.00"),), parts=[
            Part("1", PartNature.PRIVATE, "Appartement + Garage", SurfaceBreakdown(
                inside_title=Decimal("87"), excluding_balcony=Decimal("87"),
                courtyard=Decimal("16"), garage=Decimal("15"),
            ), "Dont cour=16m², dont garage=15m²", description="un appartement à usage d’habitation et garage de 87m² qui contient : salon, 2 chambres, cuisine, SDB, W.C en r.s.e, hall, dont la cour de 16m² et dont garage de 15m²."),
            Part("2", PartNature.COMMON, "Entrée + Cage d'escaliers", SurfaceBreakdown(inside_title=Decimal("6")), description="l’entrée et cage d'escaliers de 6m²."),
            Part("3", PartNature.COMMON, "Murs, piliers et gaines", SurfaceBreakdown(inside_title=Decimal("7")), description="des murs, piliers et gaines de 7m²."),
        ]),
        Level("Premier Étage", 1, (Decimal("3.40"),), (Decimal("6.40"),), (Decimal("3.00"),), parts=[
            Part("4-4a", PartNature.PRIVATE, "Appartement", SurfaceBreakdown(
                inside_title=Decimal("69"), overhang=Decimal("11"),
                excluding_balcony=Decimal("76"), balcony=Decimal("4"),
            ), "4a = 11m² en surplomb", description="un appartement à usage d’habitation de 80m², dont 11m² en surplomb, qui contient : salon, cuisine avec balcon, 2 chambres dont une avec placard, SDB, W.C et hall."),
            Part("3-3a", PartNature.COMMON, "Murs, piliers et gaines", SurfaceBreakdown(
                inside_title=Decimal("6"), overhang=Decimal("2"),
            ), "3a = 2m² en surplomb", description="des murs, piliers et gaines de 8m², dont 2m² en surplomb."),
            Part("2", PartNature.COMMON, "Cage d'escaliers", SurfaceBreakdown(inside_title=Decimal("9")), description="une cage d'escaliers de 9m²."),
            Part("5", PartNature.COMMON, "Vide sur cour", SurfaceBreakdown(inside_title=Decimal("16")), description="vide sur cour de 16m²."),
        ]),
        Level("Deuxième Étage", 2, (Decimal("6.60"),), (Decimal("9.60"),), (Decimal("3.00"),), parts=[
            Part("6-6a", PartNature.PRIVATE, "Appartement", SurfaceBreakdown(
                inside_title=Decimal("69"), overhang=Decimal("11"),
                excluding_balcony=Decimal("76"), balcony=Decimal("4"),
            ), "6a = 11m² en surplomb", description="un appartement à usage d’habitation de 80m², dont 11m² en surplomb, qui contient : salon, cuisine avec balcon, 2 chambres dont une avec placard, SDB, W.C et hall."),
            Part("3-3a", PartNature.COMMON, "Murs, piliers et gaines", SurfaceBreakdown(
                inside_title=Decimal("6"), overhang=Decimal("2"),
            ), "3a = 2m² en surplomb", description="des murs, piliers et gaines de 8m², dont 2m² en surplomb."),
            Part("2", PartNature.COMMON, "Cage d'escaliers", SurfaceBreakdown(inside_title=Decimal("9")), description="une cage d'escaliers de 9m²."),
            Part("5", PartNature.COMMON, "Vide sur cour", SurfaceBreakdown(inside_title=Decimal("16")), description="vide sur cour de 16m²."),
        ]),
        Level("Terrasse", 3, (Decimal("9.80"),), (), (), parts=[
            Part("7-7a", PartNature.COMMON, "Terrasse", SurfaceBreakdown(
                inside_title=Decimal("69"), overhang=Decimal("11"),
            ), "7a = 11m² en surplomb", description="une terrasse de 80m², dont 11m² en surplomb."),
            Part("3-3a", PartNature.COMMON, "Murs, piliers et gaines", SurfaceBreakdown(
                inside_title=Decimal("6"), overhang=Decimal("2"),
            ), "3a = 2m² en surplomb", description="des murs, piliers et gaines de 8m², dont 2m² en surplomb."),
            Part("2", PartNature.COMMON, "Cage d'escaliers", SurfaceBreakdown(inside_title=Decimal("9")), description="une cage d'escaliers de 9m²."),
            Part("5", PartNature.COMMON, "Vide sur cour", SurfaceBreakdown(inside_title=Decimal("16")), description="vide sur cour de 16m²."),
        ]),
    ])
