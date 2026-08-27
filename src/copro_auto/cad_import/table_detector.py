from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from .dxf_loader import DxfLineItem, DxfLoadResult, DxfTextItem, search_key
from .models import CadConfidence


@dataclass(slots=True)
class DetectedRow:
    index: str
    private: bool
    inside_title: Decimal
    total_with_overhang: Decimal
    consistency: str
    observations: str
    confidence: CadConfidence
    evidence: list[DxfTextItem] = field(default_factory=list)


@dataclass(slots=True)
class DetectedTable:
    anchor: DxfTextItem
    title: str
    cote_text: str
    x_min: float
    x_max: float
    top_y: float
    bottom_y: float
    header_bottom_y: float
    columns: list[float]
    rows: list[DetectedRow]
    confidence: CadConfidence
    texts: list[DxfTextItem] = field(default_factory=list)


def _length(line: DxfLineItem) -> float:
    return abs(line.end_x - line.start_x) + abs(line.end_y - line.start_y)


def _cell_index(columns: list[float], x: float) -> int:
    return max(0, min(len(columns) - 2, bisect.bisect_right(columns, x) - 1))


def _find_label_cell(items: list[DxfTextItem], columns: list[float], needle: str, default: int) -> int:
    match = next((item for item in items if needle in search_key(item.text)), None)
    return _cell_index(columns, match.x) if match else default


def _decimal_from_items(items: list[DxfTextItem]) -> Decimal:
    for item in sorted(items, key=lambda value: (-value.y, value.x)):
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", item.text)
        if not match:
            continue
        try:
            return Decimal(match.group(0).replace(",", "."))
        except InvalidOperation:
            continue
    return Decimal("0")


def _join_index(items: list[DxfTextItem]) -> str:
    fragments = [re.sub(r"\s+", "", item.text) for item in sorted(items, key=lambda value: value.x)]
    return "".join(fragment for fragment in fragments if fragment).strip("- ")


def _join_cell(items: list[DxfTextItem]) -> str:
    ordered = sorted(items, key=lambda value: (-value.y, value.x))
    return " ".join(item.text.strip() for item in ordered if item.text.strip()).strip()


def _clean_observation(value: str) -> str:
    value = " ".join(value.split())
    value = re.sub(r"(?:^|\s)2\s+(?=dont\b)", " ", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"m(?:\s*2)?\b", "m²", value, flags=re.IGNORECASE)
    suffix = "a" if re.search(r"(?:^|\s)a(?:\s|$)", value, re.IGNORECASE) else ""
    base = re.search(r"(\d+)\s*=\s*([0-9.,]+)\s*m(?:\s+en\s+surplomb)?", value, re.IGNORECASE)
    if base:
        amount = base.group(2).replace(".", ",")
        return f"{base.group(1)}{suffix} = {amount} m² en surplomb"
    return value


def _grid_for_anchor(source: DxfLoadResult, anchor: DxfTextItem) -> tuple[list[float], float, float, float, CadConfidence]:
    candidates = []
    for line in source.lines:
        if not line.horizontal or _length(line) < max(5.0, anchor.height * 20):
            continue
        x_min, x_max = sorted((line.start_x, line.end_x))
        if x_min <= anchor.x <= x_max and anchor.y - 0.55 <= line.start_y <= anchor.y + 0.30:
            candidates.append(line)
    if not candidates:
        width = max(anchor.height * 65, 12.0)
        x_min = anchor.x - anchor.height * 3
        x_max = x_min + width
        columns = [x_min + width * fraction for fraction in (0, .19, .29, .37, .45, .49, .57, .65, .82, 1)]
        return columns, anchor.y - 0.1, anchor.y - max(3.0, anchor.height * 18), anchor.y - 1.0, CadConfidence.LOW

    top = max(candidates, key=_length)
    x_min, x_max = sorted((top.start_x, top.end_x))
    join_tolerance = max(0.08, anchor.height)
    same_height = [
        line for line in source.lines
        if line.horizontal and abs(line.start_y - top.start_y) <= 1e-4
        and _length(line) >= max(1.0, anchor.height * 8)
    ]
    changed = True
    while changed:
        changed = False
        for line in same_height:
            line_min, line_max = sorted((line.start_x, line.end_x))
            if line_max < x_min - join_tolerance or line_min > x_max + join_tolerance:
                continue
            merged_min, merged_max = min(x_min, line_min), max(x_max, line_max)
            if merged_min != x_min or merged_max != x_max:
                x_min, x_max = merged_min, merged_max
                changed = True
    top_y = top.start_y
    header_reach = max(0.65, anchor.height * 5)
    verticals = [
        line for line in source.lines
        if line.vertical and x_min - 0.05 <= line.start_x <= x_max + 0.05
        and min(line.start_y, line.end_y) < top_y - 0.5
        and max(line.start_y, line.end_y) >= top_y - header_reach
    ]
    if len(verticals) < 5:
        width = x_max - x_min
        columns = [x_min + width * fraction for fraction in (0, .19, .29, .37, .45, .49, .57, .65, .82, 1)]
        return columns, top_y, top_y - max(3.0, anchor.height * 18), top_y - 1.0, CadConfidence.MEDIUM

    bottom_y = min(min(line.start_y, line.end_y) for line in verticals)
    columns = sorted({round(line.start_x, 5) for line in verticals} | {round(x_min, 5), round(x_max, 5)})
    inner_horizontal = [
        line.start_y for line in source.lines
        if line.horizontal and bottom_y + 0.4 < line.start_y < top_y - 0.25
        and min(line.start_x, line.end_x) <= x_min + 0.1
        and max(line.start_x, line.end_x) >= x_max - 0.1
    ]
    header_bottom = max(inner_horizontal, default=top_y - 1.0)
    return columns, top_y, bottom_y, header_bottom, CadConfidence.HIGH


def _rows_from_region(
    items: list[DxfTextItem], columns: list[float], bottom_y: float, header_bottom_y: float,
    grid_confidence: CadConfidence,
) -> list[DetectedRow]:
    private_column = _find_label_cell(items, columns, "privative", 2)
    common_column = _find_label_cell(items, columns, "commune", 3)
    inside_column = _find_label_cell(items, columns, "interieur", 5)
    total_column = _find_label_cell(items, columns, "surplomb", 6)
    consistency_column = _find_label_cell(items, columns, "consistance", 7)
    observation_column = _find_label_cell(items, columns, "observation", 8)
    data = [item for item in items if bottom_y + 0.18 < item.y < header_bottom_y - 0.03]

    index_groups: list[tuple[int, list[DxfTextItem]]] = []
    for column in (private_column, common_column):
        fragments = [item for item in data if _cell_index(columns, item.x) == column]
        for item in sorted(fragments, key=lambda value: -value.y):
            if index_groups and index_groups[-1][0] == column:
                center = sum(value.y for value in index_groups[-1][1]) / len(index_groups[-1][1])
                if abs(center - item.y) <= max(0.22, item.height * 2.2):
                    index_groups[-1][1].append(item)
                    continue
            index_groups.append((column, [item]))
    index_groups.sort(key=lambda entry: -sum(item.y for item in entry[1]) / len(entry[1]))
    for entry in list(index_groups):
        column, group = entry
        if any(re.search(r"\d", item.text) for item in group):
            continue
        center_y = sum(item.y for item in group) / len(group)
        left_x = min(item.x for item in group)
        target = next((
            candidate for candidate in index_groups
            if candidate is not entry
            and any(re.search(r"\d", item.text) for item in candidate[1])
            and abs(sum(item.y for item in candidate[1]) / len(candidate[1]) - center_y) <= 0.22
            and 0 < left_x - max(item.x for item in candidate[1]) <= 0.65
        ), None)
        if target is not None:
            target[1].extend(group)
            index_groups.remove(entry)
    grouped_ids = {id(item) for _column, group in index_groups for item in group}
    suffixes = [
        item for item in data
        if id(item) not in grouped_ids and search_key(item.text) in {"a", "b"}
    ]
    for _column, group in index_groups:
        center_y = sum(item.y for item in group) / len(group)
        right_x = max(item.x for item in group)
        suffix = next((
            item for item in suffixes
            if abs(item.y - center_y) <= max(0.22, item.height * 2.2) and 0 < item.x - right_x <= 0.65
        ), None)
        if suffix is not None:
            group.append(suffix)
            suffixes.remove(suffix)

    rows: list[DetectedRow] = []
    centers = [sum(item.y for item in group) / len(group) for _column, group in index_groups]
    paddings = [max(0.06, max(item.height for item in group) * 1.1) for _column, group in index_groups]
    for position, ((column, index_items), center) in enumerate(zip(index_groups, centers)):
        upper = header_bottom_y if position == 0 else center + paddings[position]
        lower = bottom_y if position == len(centers) - 1 else centers[position + 1] + paddings[position + 1]
        row_items = [item for item in data if lower <= item.y < upper]
        by_column: dict[int, list[DxfTextItem]] = {}
        for item in row_items:
            by_column.setdefault(_cell_index(columns, item.x), []).append(item)
        index = _join_index(index_items)
        if not index or not re.search(r"\d", index):
            continue
        inside = _decimal_from_items(by_column.get(inside_column, []))
        total = _decimal_from_items(by_column.get(total_column, []))
        if total == 0 and inside:
            total = inside
        confidence = grid_confidence if inside or total else CadConfidence.LOW
        rows.append(DetectedRow(
            index=index,
            private=column == private_column,
            inside_title=inside,
            total_with_overhang=total,
            consistency=_join_cell(by_column.get(consistency_column, [])),
            observations=_clean_observation(_join_cell(by_column.get(observation_column, []))),
            confidence=confidence,
            evidence=row_items,
        ))
    return rows


def detect_containment_tables(source: DxfLoadResult) -> list[DetectedTable]:
    anchors = [item for item in source.texts if "tableau des contenances" in search_key(item.text)]
    anchors.sort(key=lambda item: -item.y)
    tables: list[DetectedTable] = []
    for anchor in anchors:
        columns, top_y, bottom_y, header_bottom, confidence = _grid_for_anchor(source, anchor)
        x_min, x_max = columns[0], columns[-1]
        items = [
            item for item in source.texts
            if x_min - 0.1 <= item.x <= x_max + 0.1 and bottom_y - 0.1 <= item.y <= anchor.y + 0.5
        ]
        nearby_margin = max(1.0, anchor.height * 8)
        nearby = [
            item for item in source.texts
            if x_min - nearby_margin <= item.x <= x_max + nearby_margin
            and anchor.y < item.y <= anchor.y + max(2.2, anchor.height * 15)
        ]
        title_item = next((item for item in sorted(nearby, key=lambda value: value.y) if search_key(item.text).startswith("plan ")), None)
        cote_item = next((item for item in sorted(nearby, key=lambda value: value.y) if "cote" in search_key(item.text)), None)
        header_key = search_key(" ".join(
            item.text for item in items if header_bottom - 0.05 <= item.y <= top_y + 0.05
        ))
        required_headers = ("privative", "commune", "interieur", "surplomb", "consistance", "observation")
        if len(columns) < 7 or any(header not in header_key for header in required_headers):
            confidence = CadConfidence.MEDIUM if confidence is CadConfidence.HIGH else confidence
        rows = _rows_from_region(items, columns, bottom_y, header_bottom, confidence)
        if any(not row.consistency.strip() for row in rows):
            confidence = CadConfidence.MEDIUM if confidence is CadConfidence.HIGH else confidence
            for row in rows:
                if not row.consistency.strip() and row.confidence is CadConfidence.HIGH:
                    row.confidence = CadConfidence.MEDIUM
        tables.append(DetectedTable(
            anchor=anchor,
            title=title_item.text if title_item else "",
            cote_text=cote_item.text if cote_item else "",
            x_min=x_min,
            x_max=x_max,
            top_y=top_y,
            bottom_y=bottom_y,
            header_bottom_y=header_bottom,
            columns=columns,
            rows=rows,
            confidence=confidence,
            texts=items,
        ))
    return tables
