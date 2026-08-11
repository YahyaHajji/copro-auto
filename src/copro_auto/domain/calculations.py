from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR

from .models import Part, PartNature, Project


@dataclass(frozen=True, slots=True)
class Share:
    part_id: str
    part_index: str
    reference_surface: Decimal
    ten_thousandths: int

    @property
    def percentage(self) -> Decimal:
        return Decimal(self.ten_thousandths) / Decimal(100)


def largest_remainder(surfaces: list[Decimal], target: int = 10_000) -> list[int]:
    if not surfaces:
        raise ValueError("Au moins une surface privative est requise.")
    if target <= 0:
        raise ValueError("La cible des tantièmes doit être positive.")
    if any(surface <= 0 for surface in surfaces):
        raise ValueError("Toutes les surfaces privatives doivent être positives.")

    total_surface = sum(surfaces, Decimal("0"))
    exact = [surface * Decimal(target) / total_surface for surface in surfaces]
    allocated = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
    remainders = [exact[i] - Decimal(allocated[i]) for i in range(len(exact))]
    missing = target - sum(allocated)
    ranked = sorted(range(len(surfaces)), key=lambda i: (-remainders[i], i))
    for index in ranked[:missing]:
        allocated[index] += 1
    if sum(allocated) != target:
        raise RuntimeError("La répartition calculée n'est pas égale à la cible.")
    return allocated


def private_parts(project: Project) -> list[Part]:
    return [
        part
        for level in sorted(project.levels, key=lambda item: item.order)
        for part in level.parts
        if part.nature is PartNature.PRIVATE
    ]


def calculate_shares(project: Project) -> list[Share]:
    parts = private_parts(project)
    surfaces = [part.surfaces.cadastral_total for part in parts]
    allocations = largest_remainder(surfaces)
    return [
        Share(part.id, part.index, surface, allocation)
        for part, surface, allocation in zip(parts, surfaces, allocations, strict=True)
    ]


def level_totals(project: Project) -> dict[str, dict[str, Decimal]]:
    result: dict[str, dict[str, Decimal]] = {}
    for level in project.levels:
        inside = sum((part.surfaces.inside_title for part in level.parts), Decimal("0"))
        with_overhang = sum((part.surfaces.cadastral_total for part in level.parts), Decimal("0"))
        result[level.id] = {"inside_title": inside, "with_overhang": with_overhang}
    return result

