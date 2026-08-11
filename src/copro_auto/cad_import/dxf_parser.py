from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf

from copro_auto.domain.models import EvidenceSource, SourceEvidence


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CadValue:
    field: str
    value: str
    evidence: SourceEvidence


@dataclass(slots=True)
class CadImportResult:
    source: Path
    values: dict[str, CadValue] = field(default_factory=dict)
    texts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _clean_mtext(text: str) -> str:
    value = text.replace("\\P", "\n").replace("%%d", "°").replace("%%c", "Ø").replace("%%p", "±")
    value = re.sub(r"\\[A-Za-z][^;]*;", "", value)
    return " ".join(value.replace("{", "").replace("}", "").split())


def _put(result: CadImportResult, field_name: str, value: str, entity: object, source_type: EvidenceSource) -> None:
    if field_name in result.values or not value.strip():
        return
    handle = getattr(getattr(entity, "dxf", None), "handle", "") or ""
    result.values[field_name] = CadValue(field_name, value.strip(), SourceEvidence(
        source=source_type,
        raw_value=value.strip(),
        source_file=str(result.source),
        entity_reference=str(handle),
    ))


PATTERNS = (
    ("identity.land_title", r"(?:Titre\s*(?:N[°ºo]|:)?|T\.)\s*:?[T ]*\s*([0-9]+/[0-9]+)"),
    ("identity.property_name", r"(?:Propriété dite\s*:|Propriete dite\s*:)[ ]*(.+?)(?=\s+(?:Situation|Titre|Plan|Echelle|Échelle)\b|$)"),
    ("identity.prefecture", r"Préfecture(?: et Commune)? de\s+([^,]+)"),
    ("identity.subdivision", r"[Ll]otiss(?:e)?ment\s+([^,|]+?)(?=\s+(?:Parties|Echelle|Échelle|Plan|Titre)\b|$)"),
)


def _extract_from_text(result: CadImportResult, text: str, entity: object, source: EvidenceSource) -> None:
    for field_name, pattern in PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            _put(result, field_name, match.group(1), entity, source)


def _table_texts(entity: object) -> list[str]:
    """Read native AutoCAD table cells when exposed by the DXF adapter."""
    rows = int(getattr(getattr(entity, "dxf", None), "nrows", 0) or getattr(entity, "nrows", 0) or 0)
    columns = int(getattr(getattr(entity, "dxf", None), "ncols", 0) or getattr(entity, "ncols", 0) or 0)
    getter = getattr(entity, "get_cell_value", None) or getattr(entity, "get_text", None)
    if not rows or not columns or not callable(getter):
        return []
    values: list[str] = []
    for row in range(rows):
        cells = []
        for column in range(columns):
            try:
                value = _clean_mtext(str(getter(row, column)))
            except (IndexError, TypeError, ValueError):
                value = ""
            if value:
                cells.append(value)
        if cells:
            values.append(" | ".join(cells))
    return values


def _spatial_rows(items: list[tuple[float, float, float, str, object]]) -> list[tuple[str, object]]:
    """Join drawn TEXT primitives that share a baseline, left to right."""
    rows: list[dict[str, object]] = []
    for x, y, height, text, entity in sorted(items, key=lambda item: (-item[1], item[0])):
        selected = None
        for row in rows:
            tolerance = max(0.02, min(float(row["height"]), height) * 0.35)
            if abs(float(row["y"]) - y) <= tolerance:
                selected = row
                break
        if selected is None:
            selected = {"y": y, "height": max(height, 0.01), "cells": [], "entity": entity}
            rows.append(selected)
        selected["cells"].append((x, text, height))
    output: list[tuple[str, object]] = []
    for row in rows:
        cells = sorted(row["cells"], key=lambda item: item[0])
        clusters: list[list[tuple[float, str, float]]] = []
        for cell in cells:
            if not clusters:
                clusters.append([cell])
                continue
            previous_x, previous_text, previous_height = clusters[-1][-1]
            estimated_end = previous_x + max(previous_height, 0.05) * len(previous_text) * 0.62
            gap = cell[0] - estimated_end
            if cell[0] <= previous_x or gap > max(1.5, previous_height * 8):
                clusters.append([cell])
            else:
                clusters[-1].append(cell)
        for cluster in clusters:
            combined = " ".join(text.strip() for _x, text, _height in cluster if text.strip())
            if combined:
                output.append((combined, row["entity"]))
    return output


def parse_dxf(path: str | Path) -> CadImportResult:
    source = Path(path).resolve(strict=True)
    try:
        document = ezdxf.readfile(source)
    except (OSError, ezdxf.DXFError) as exc:
        raise ValueError(f"DXF illisible : {exc}") from exc
    result = CadImportResult(source=source)
    entities = list(document.modelspace())
    spatial_items: list[tuple[float, float, float, str, object]] = []
    for entity in entities:
        kind = entity.dxftype()
        if kind in {"ACAD_TABLE", "TABLE"}:
            for text in _table_texts(entity):
                result.texts.append(text)
                _extract_from_text(result, text, entity, EvidenceSource.DXF_TABLE)
            continue
        if kind == "TEXT":
            text = _clean_mtext(entity.dxf.text)
            insert = entity.dxf.insert
            spatial_items.append((float(insert.x), float(insert.y), float(entity.dxf.height or 0.1), text, entity))
        elif kind == "MTEXT":
            text = _clean_mtext(entity.plain_text())
            insert = entity.dxf.insert
            spatial_items.append((float(insert.x), float(insert.y), float(entity.dxf.char_height or 0.1), text, entity))
        else:
            continue
        if text:
            result.texts.append(text)
    for text, entity in _spatial_rows(spatial_items):
        _extract_from_text(result, text, entity, EvidenceSource.DXF_TEXT)
    for entity in entities:
        kind = entity.dxftype()
        if kind == "TEXT":
            _extract_from_text(result, _clean_mtext(entity.dxf.text), entity, EvidenceSource.DXF_TEXT)
        elif kind == "MTEXT":
            _extract_from_text(result, _clean_mtext(entity.plain_text()), entity, EvidenceSource.DXF_TEXT)
    if not result.texts:
        result.warnings.append("Aucun texte exploitable n'a été trouvé dans le dessin.")
    LOGGER.info("dxf_parsed entities=%d texts=%d fields=%d", len(entities), len(result.texts), len(result.values))
    return result
