from __future__ import annotations

import logging
import re
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path

from copro_auto.domain.models import EvidenceSource, PartNature, SourceEvidence, decimal_tuple_from

from .dxf_loader import DxfLoadResult, DxfNativeTable, DxfTextItem, load_dxf, normalize_text, search_key
from .models import CadCandidate, CadConfidence, CadImportDraft, CadLevelDraft, CadPartDraft
from .table_detector import DetectedTable, detect_containment_tables


LOGGER = logging.getLogger(__name__)
CadValue = CadCandidate
CadImportResult = CadImportDraft


PATTERNS = (
    ("identity.land_title", r"(?:Titre\s*(?:N[°ºo]|:)?|T\.)\s*:?[T ]*\s*([0-9]+/[0-9]+)"),
    ("identity.property_name", r"(?:Propriété dite\s*:|Propriete dite\s*:)[ ]*(.+?)(?=\s+(?:Situation|Titre|Plan|Echelle|Échelle)\b|$)"),
    ("identity.prefecture", r"Pr[eé]fecture\b(?:\s+et\s+Commune\b)?(?:\s+de)?\s*:?\s*([^,]+)"),
    ("identity.commune", r"(?:Pr[eé]fecture\s+et\s+)?Commune\b(?:\s+de)?\s*:?\s*([^,]+)"),
    ("identity.subdivision", r"[Ll]otiss(?:e)?ment\s+([^,|]+?)(?=\s+(?:Parties|Echelle|Échelle|Plan|Titre)\b|$)"),
)


def _spatial_rows(items: list[DxfTextItem]) -> list[tuple[str, DxfTextItem]]:
    rows: list[dict[str, object]] = []
    for item in sorted(items, key=lambda value: (-value.y, value.x)):
        selected = None
        for row in rows:
            tolerance = max(0.02, min(float(row["height"]), item.height) * 0.35)
            if abs(float(row["y"]) - item.y) <= tolerance:
                selected = row
                break
        if selected is None:
            selected = {"y": item.y, "height": max(item.height, 0.01), "cells": [], "item": item}
            rows.append(selected)
        selected["cells"].append(item)
    output: list[tuple[str, DxfTextItem]] = []
    for row in rows:
        cells = sorted(row["cells"], key=lambda value: value.x)
        clusters: list[list[DxfTextItem]] = []
        for cell in cells:
            if not clusters:
                clusters.append([cell])
                continue
            previous = clusters[-1][-1]
            estimated_end = previous.x + max(previous.height, 0.05) * len(previous.text) * 0.62
            if cell.x <= previous.x or cell.x - estimated_end > max(1.5, previous.height * 8):
                clusters.append([cell])
            else:
                clusters[-1].append(cell)
        for cluster in clusters:
            combined = " ".join(cell.text for cell in cluster if cell.text)
            if combined:
                output.append((combined, cluster[0]))
    return output


def _evidence(source: Path, item: DxfTextItem, raw_value: str | None = None) -> SourceEvidence:
    return SourceEvidence(
        source=EvidenceSource.DXF_TEXT,
        raw_value=raw_value if raw_value is not None else item.text,
        source_file=str(source),
        entity_reference=item.entity_reference,
    )


def _extract_identity(loaded: DxfLoadResult) -> dict[str, CadCandidate]:
    values: dict[str, CadCandidate] = {}
    candidates = _spatial_rows(loaded.texts) + [(item.text, item) for item in loaded.texts]
    for text, item in candidates:
        for field_name, pattern in PATTERNS:
            if field_name in values:
                continue
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.group(1).strip():
                values[field_name] = CadCandidate(
                    field=field_name,
                    value=match.group(1).strip(),
                    confidence=CadConfidence.MEDIUM,
                    evidence=_evidence(loaded.source, item, match.group(0)),
                )
    return values


def _level_name(title: str, position: int) -> str:
    value = re.sub(
        r"^\s*Plan\s+(?:(?:du|de\s+la|des)\s+)?", "", normalize_text(title), flags=re.IGNORECASE,
    ).strip()
    key = re.sub(r"[^a-z0-9]+", "", search_key(value))
    aliases = {
        "rdc": "Rez-de-chaussée",
        "rezdechaussee": "Rez-de-chaussée",
        "1eretage": "Premier Étage",
        "premieretage": "Premier Étage",
        "2emeetage": "Deuxième Étage",
        "deuxiemeetage": "Deuxième Étage",
        "3emeetage": "Troisième Étage",
        "troisiemeetage": "Troisième Étage",
        "4emeetage": "Quatrième Étage",
        "quatriemeetage": "Quatrième Étage",
        "soussol": "Sous-sol",
        "mezzanine": "Mezzanine",
        "terrasse": "Terrasse",
    }
    return aliases.get(key, value or f"Niveau importé {position + 1}")


NUMBER_PATTERN = re.compile(r"[+-]?\s*\d+(?:[.,]\d+)?")
ELEVATION_PATTERN = re.compile(
    r"^(?:de\s+la|des|a\s+partir\s+de\s+la)\s+cotes?\s*:?\s*"
    r"(?P<starts>.*?)"
    r"(?:\s+(?:a\s+la|aux)\s+cotes?\s*:?\s*(?P<ends>.*))?$",
    re.IGNORECASE,
)


def _decimal_numbers(text: str) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for number in NUMBER_PATTERN.findall(text):
        try:
            value = Decimal(number.replace(" ", "").replace(",", "."))
        except InvalidOperation:
            continue
        if value not in values:
            values.append(value)
    return tuple(values)


def _derived_heights(
    starts: tuple[Decimal, ...], ends: tuple[Decimal, ...],
) -> tuple[tuple[Decimal, ...], bool]:
    if not starts or not ends:
        return (), True
    if len(starts) == 1:
        pairs = ((starts[0], end) for end in ends)
    elif len(ends) == 1:
        pairs = ((start, ends[0]) for start in starts)
    elif len(starts) == len(ends):
        pairs = zip(starts, ends)
    else:
        return (), False
    heights = decimal_tuple_from(end - start for start, end in pairs)
    if any(height <= 0 for height in heights):
        return (), False
    return heights, True


def _elevations(
    text: str,
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...], tuple[Decimal, ...], bool]:
    normalized = search_key(text)
    structured = ELEVATION_PATTERN.match(normalized)
    if structured:
        starts = _decimal_numbers(structured.group("starts") or "")
        ends = _decimal_numbers(structured.group("ends") or "")
        heights, deterministic = _derived_heights(starts, ends)
        ambiguous = not starts or (bool(ends) and not deterministic)
        return starts, ends, heights, ambiguous

    values = _decimal_numbers(normalized)
    if not values:
        return (), (), (), False
    # Preserve every value for review, but do not calculate a height when the
    # linguistic start/end markers are missing.
    return values[:1], values[1:], (), len(values) > 1


def _exact_decimal(text: str) -> Decimal | None:
    match = re.fullmatch(r"\s*([+-]?\s*\d+(?:[.,]\d+)?)\s*(?:m)?\s*", normalize_text(text), re.IGNORECASE)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None


def _height_confirmation_evidence(
    loaded: DxfLoadResult,
    *,
    anchor: DxfTextItem,
    x_min: float,
    x_max: float,
    heights: tuple[Decimal, ...],
) -> list[SourceEvidence]:
    if not heights:
        return []
    width = max(1.0, x_max - x_min)
    margin = max(1.0, width * 0.2)
    coupe_labels = [
        item for item in loaded.texts
        if x_min - margin <= item.x <= x_max + margin
        and 2 <= anchor.y - item.y <= 60
        and "coupe" in search_key(item.text)
        and "hauteur" in search_key(item.text)
    ]
    if not coupe_labels:
        return []
    coupe = min(coupe_labels, key=lambda item: abs(anchor.y - item.y))
    evidence: list[SourceEvidence] = []
    for height in heights:
        matches = [
            item for item in loaded.texts
            if x_min - margin <= item.x <= x_max + margin
            and 0 < coupe.y - item.y <= 35
            and _exact_decimal(item.text) == height
        ]
        if not matches:
            return []
        selected = min(matches, key=lambda item: abs(item.y - coupe.y))
        evidence.append(_evidence(loaded.source, selected))
    return evidence


def _confidence_with_heights(
    table_confidence: CadConfidence,
    heights: tuple[Decimal, ...],
    confirmed: bool,
    ambiguous: bool,
) -> CadConfidence:
    if table_confidence is CadConfidence.LOW:
        return CadConfidence.LOW
    if ambiguous or (heights and not confirmed):
        return CadConfidence.MEDIUM
    return table_confidence


def _table_to_level(loaded: DxfLoadResult, table: DetectedTable, position: int) -> CadLevelDraft:
    starts, ends, heights, ambiguous = _elevations(table.cote_text)
    evidence = [_evidence(loaded.source, table.anchor)]
    height_evidence = _height_confirmation_evidence(
        loaded,
        anchor=table.anchor,
        x_min=table.x_min,
        x_max=table.x_max,
        heights=heights,
    )
    evidence.extend(height_evidence)
    parts: list[CadPartDraft] = []
    for row in table.rows:
        row_evidence = [_evidence(loaded.source, item) for item in row.evidence if item.entity_reference]
        parts.append(CadPartDraft(
            index=row.index,
            nature=PartNature.PRIVATE if row.private else PartNature.COMMON,
            consistency=row.consistency,
            inside_title=row.inside_title,
            overhang=max(Decimal("0"), row.total_with_overhang - row.inside_title),
            observations=row.observations,
            confidence=row.confidence,
            evidence=row_evidence,
        ))
    return CadLevelDraft(
        name=_level_name(table.title, position),
        order=position,
        start_elevations=starts,
        end_elevations=ends,
        interior_heights=heights,
        parts=parts,
        confidence=_confidence_with_heights(table.confidence, heights, bool(height_evidence), ambiguous),
        elevation_ambiguous=ambiguous,
        evidence=evidence,
    )


def _native_column(headers: list[str], needle: str, default: int) -> int:
    return next((index for index, value in enumerate(headers) if needle in search_key(value)), default)


def _native_decimal(value: str) -> Decimal:
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", value)
    if not match:
        return Decimal("0")
    try:
        return Decimal(match.group(0).replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


def _native_table_to_level(loaded: DxfLoadResult, table: DxfNativeTable, position: int) -> CadLevelDraft:
    width = max((len(row) for row in table.cells), default=0)
    header_end = 0
    for row_index, row in enumerate(table.cells[:6]):
        joined = search_key(" ".join(row))
        header_markers = sum(word in joined for word in ("privative", "commune", "consistance", "surplomb"))
        if header_markers >= 2:
            header_end = row_index
    headers = [" ".join(row[column] for row in table.cells[:header_end + 1] if column < len(row)) for column in range(width)]
    private_column = _native_column(headers, "privative", 0)
    common_column = _native_column(headers, "commune", min(1, width - 1))
    inside_column = _native_column(headers, "interieur", min(2, width - 1))
    total_column = _native_column(headers, "surplomb", min(3, width - 1))
    consistency_column = _native_column(headers, "consistance", min(4, width - 1))
    observation_column = _native_column(headers, "observation", min(5, width - 1))
    source_evidence = SourceEvidence(
        source=EvidenceSource.DXF_TABLE,
        raw_value="TABLE",
        source_file=str(loaded.source),
        entity_reference=table.entity_reference,
    )
    parts: list[CadPartDraft] = []
    for row in table.cells[header_end + 1:]:
        private_index = row[private_column].strip() if private_column < len(row) else ""
        common_index = row[common_column].strip() if common_column < len(row) else ""
        index = private_index or common_index
        if not index or search_key(index).startswith("total"):
            continue
        inside = _native_decimal(row[inside_column] if inside_column < len(row) else "")
        total = _native_decimal(row[total_column] if total_column < len(row) else "") or inside
        parts.append(CadPartDraft(
            index=re.sub(r"\s+", "", index),
            nature=PartNature.PRIVATE if private_index else PartNature.COMMON,
            consistency=row[consistency_column].strip() if consistency_column < len(row) else "",
            inside_title=inside,
            overhang=max(Decimal("0"), total - inside),
            observations=row[observation_column].strip() if observation_column < len(row) else "",
            confidence=CadConfidence.HIGH,
            evidence=[deepcopy(source_evidence)],
        ))
    nearby = sorted(loaded.texts, key=lambda item: (abs(item.y - table.y), abs(item.x - table.x)))
    title = next((item.text for item in nearby if search_key(item.text).startswith("plan ")), "")
    cote_text = next((item.text for item in nearby if "cote" in search_key(item.text)), "")
    starts, ends, heights, ambiguous = _elevations(cote_text)
    anchor = next((item for item in nearby if item.text == cote_text), None)
    if anchor is None:
        anchor = DxfTextItem(cote_text, table.x, table.y, 0.1, table.entity_reference)
    height_evidence = _height_confirmation_evidence(
        loaded,
        anchor=anchor,
        x_min=table.x - 1,
        x_max=table.x + 20,
        heights=heights,
    )
    return CadLevelDraft(
        name=_level_name(title, position), order=position,
        start_elevations=starts, end_elevations=ends, interior_heights=heights, parts=parts,
        confidence=_confidence_with_heights(CadConfidence.HIGH, heights, bool(height_evidence), ambiguous),
        elevation_ambiguous=ambiguous,
        evidence=[source_evidence, *height_evidence],
    )


ROOM_WORDS = re.compile(
    r"\b(salon|séjour|sejour|chambre|cuisine|s\.?d\.?b|w\.?c|garage|hall|placard)\b",
    re.IGNORECASE,
)


def _add_room_suggestions(loaded: DxfLoadResult, tables: list[DetectedTable], levels: list[CadLevelDraft]) -> None:
    centers = [table.anchor.y for table in tables]
    for index, (table, level) in enumerate(zip(tables, levels)):
        private = [part for part in level.parts if part.nature is PartNature.PRIVATE]
        if len(private) != 1:
            continue
        upper = float("inf") if index == 0 else (centers[index - 1] + centers[index]) / 2
        lower = float("-inf") if index == len(tables) - 1 else (centers[index] + centers[index + 1]) / 2
        labels: list[str] = []
        for item in loaded.texts:
            if not (lower < item.y <= upper) or table.x_min - 0.2 <= item.x <= table.x_max + 0.2:
                continue
            if ROOM_WORDS.search(item.text) and len(item.text) <= 80 and item.text not in labels:
                labels.append(item.text)
        if labels:
            private[0].description_suggestion = ", ".join(labels[:12])
            private[0].description_confidence = CadConfidence.LOW


def parse_dxf(path: str | Path) -> CadImportDraft:
    loaded = load_dxf(path)
    tables = detect_containment_tables(loaded) if not loaded.native_tables else []
    if loaded.native_tables:
        levels = [_native_table_to_level(loaded, table, index) for index, table in enumerate(loaded.native_tables)]
    else:
        levels = [_table_to_level(loaded, table, index) for index, table in enumerate(tables)]
    if all(level.start_elevations for level in levels):
        levels.sort(key=lambda level: level.start_elevations[0])
        for index, level in enumerate(levels):
            level.order = index
    if tables:
        _add_room_suggestions(loaded, tables, levels)
    warnings = list(loaded.warnings)
    if not tables and not loaded.native_tables:
        warnings.append("CAD_NO_CONTAINMENT_TABLE")
    for index, level in enumerate(levels):
        if not level.parts:
            warnings.append(f"CAD_LEVEL_WITHOUT_PARTS:{index}")
        if not level.start_elevations:
            warnings.append(f"CAD_LEVEL_MISSING_ELEVATION:{index}")
        if level.elevation_ambiguous:
            warnings.append(f"CAD_LEVEL_MULTIPLE_ELEVATIONS:{index}")
    result = CadImportDraft(
        source=loaded.source,
        fingerprint=loaded.fingerprint,
        size_bytes=loaded.size_bytes,
        values=_extract_identity(loaded),
        levels=levels,
        texts=[item.text for item in loaded.texts],
        warnings=warnings,
        entity_counts=loaded.entity_counts,
    )
    LOGGER.info(
        "dxf_parsed tables=%d levels=%d parts=%d fields=%d warnings=%d",
        len(tables) + len(loaded.native_tables), len(levels), result.part_count, len(result.values), len(warnings),
    )
    return result
