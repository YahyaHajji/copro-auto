from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf


LOGGER = logging.getLogger(__name__)
CORRUPTION_MARKERS = ("�", "Ã", "Â")


@dataclass(frozen=True, slots=True)
class DxfTextItem:
    text: str
    x: float
    y: float
    height: float
    entity_reference: str
    layer: str = ""


@dataclass(frozen=True, slots=True)
class DxfLineItem:
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    entity_reference: str

    @property
    def horizontal(self) -> bool:
        return abs(self.start_y - self.end_y) <= 1e-5

    @property
    def vertical(self) -> bool:
        return abs(self.start_x - self.end_x) <= 1e-5


@dataclass(frozen=True, slots=True)
class DxfNativeTable:
    cells: tuple[tuple[str, ...], ...]
    x: float
    y: float
    entity_reference: str


@dataclass(slots=True)
class DxfLoadResult:
    source: Path
    fingerprint: str
    size_bytes: int
    texts: list[DxfTextItem]
    lines: list[DxfLineItem]
    entity_counts: dict[str, int]
    native_tables: list[DxfNativeTable] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_text(value: str) -> str:
    value = value.replace("\\P", "\n").replace("%%d", "°").replace("%%c", "Ø").replace("%%p", "±")
    value = re.sub(r"\\[A-Za-z][^;]*;", "", value)
    value = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda match: chr(int(match.group(1), 16)), value)
    return " ".join(value.replace("{", "").replace("}", "").split())


def search_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", normalize_text(value))
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).casefold().split())


def _declared_encoding(raw: bytes) -> str:
    header = raw[:100_000].decode("latin-1", errors="ignore")
    match = re.search(r"\$DWGCODEPAGE\s*\r?\n\s*3\s*\r?\n([^\r\n]+)", header)
    declared = match.group(1).strip().upper() if match else ""
    if declared.startswith("ANSI_") and declared[5:].isdigit():
        return f"cp{declared[5:]}"
    return "cp1252"


def _decode_source(raw: bytes) -> tuple[str, str]:
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        encoding = _declared_encoding(raw)
        return raw.decode(encoding, errors="replace"), encoding


def _raw_entity_texts(decoded: str) -> dict[str, str]:
    lines = decoded.splitlines()
    pairs: list[tuple[int, str]] = []
    for index in range(0, len(lines) - 1, 2):
        try:
            code = int(lines[index].strip())
        except ValueError:
            continue
        pairs.append((code, lines[index + 1]))
    output: dict[str, str] = {}
    current: list[tuple[int, str]] = []
    for code, value in pairs + [(0, "EOF")]:
        if code == 0 and current:
            handle = next((item for tag, item in current if tag == 5), "")
            parts = [item for tag, item in current if tag in (1, 3)]
            if handle and parts:
                output[handle] = normalize_text("".join(parts))
            current = []
        current.append((code, value))
    return output


def _entity_text(entity: object, raw_texts: dict[str, str]) -> str:
    dxf = getattr(entity, "dxf", None)
    handle = str(getattr(dxf, "handle", "") or "")
    raw = raw_texts.get(handle, "")
    if raw:
        return raw
    if entity.dxftype() == "TEXT":
        return normalize_text(str(entity.dxf.text))
    return normalize_text(str(entity.plain_text()))


def _collect_text(entity: object, raw_texts: dict[str, str], reference: str | None = None) -> list[DxfTextItem]:
    kind = entity.dxftype()
    if kind not in {"TEXT", "MTEXT"}:
        return []
    insert = entity.dxf.insert
    handle = reference or str(getattr(entity.dxf, "handle", "") or "")
    height = entity.dxf.height if kind == "TEXT" else entity.dxf.char_height
    text = _entity_text(entity, raw_texts)
    if not text:
        return []
    return [DxfTextItem(text, float(insert.x), float(insert.y), float(height or 0.1), handle, str(entity.dxf.layer))]


def load_dxf(path: str | Path) -> DxfLoadResult:
    source = Path(path).resolve(strict=True)
    raw = source.read_bytes()
    decoded, encoding = _decode_source(raw)
    raw_texts = _raw_entity_texts(decoded)
    try:
        document = ezdxf.readfile(source)
    except (OSError, ezdxf.DXFError) as exc:
        raise ValueError(f"DXF illisible : {exc}") from exc

    texts: list[DxfTextItem] = []
    lines: list[DxfLineItem] = []
    native_tables: list[DxfNativeTable] = []
    counts: Counter[str] = Counter()
    warnings: list[str] = []
    for entity in document.modelspace():
        kind = entity.dxftype()
        counts[kind] += 1
        if kind in {"TEXT", "MTEXT"}:
            texts.extend(_collect_text(entity, raw_texts))
        elif kind in {"ACAD_TABLE", "TABLE"}:
            rows = int(getattr(entity.dxf, "nrows", 0) or getattr(entity, "nrows", 0) or 0)
            columns = int(getattr(entity.dxf, "ncols", 0) or getattr(entity, "ncols", 0) or 0)
            getter = getattr(entity, "get_cell_value", None) or getattr(entity, "get_text", None)
            if rows and columns and callable(getter):
                cells: list[tuple[str, ...]] = []
                for row in range(rows):
                    values: list[str] = []
                    for column in range(columns):
                        try:
                            values.append(normalize_text(str(getter(row, column))))
                        except (IndexError, TypeError, ValueError):
                            values.append("")
                    cells.append(tuple(values))
                insert = getattr(entity.dxf, "insert", (0.0, 0.0, 0.0))
                insert_x = float(getattr(insert, "x", insert[0]))
                insert_y = float(getattr(insert, "y", insert[1]))
                native_tables.append(DxfNativeTable(
                    tuple(cells), insert_x, insert_y, str(getattr(entity.dxf, "handle", "") or ""),
                ))
        elif kind == "INSERT":
            insert_handle = str(getattr(entity.dxf, "handle", "") or "")
            for attribute in getattr(entity, "attribs", ()):  # attributed title blocks
                texts.extend(_collect_text(attribute, raw_texts, insert_handle))
            try:
                virtual_entities = list(entity.virtual_entities())
            except (AttributeError, ezdxf.DXFError):
                virtual_entities = []
            for virtual in virtual_entities:
                if virtual.dxftype() in {"TEXT", "MTEXT"}:
                    texts.extend(_collect_text(virtual, raw_texts, insert_handle))
        elif kind == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            lines.append(DxfLineItem(float(start.x), float(start.y), float(end.x), float(end.y), str(entity.dxf.handle)))
        elif kind == "LWPOLYLINE":
            points = [(float(point[0]), float(point[1])) for point in entity.get_points("xy")]
            if entity.closed and points:
                points.append(points[0])
            for first, second in zip(points, points[1:]):
                lines.append(DxfLineItem(first[0], first[1], second[0], second[1], str(entity.dxf.handle)))

    corrupted = [item for item in texts if any(marker in item.text for marker in CORRUPTION_MARKERS)]
    if corrupted:
        raise ValueError(
            "Le texte du DXF contient des caractères corrompus. Exportez à nouveau le dessin en DXF R2018 "
            "avec un encodage Unicode, puis réessayez."
        )
    if not texts:
        warnings.append("CAD_NO_TEXT")
    fingerprint = hashlib.sha256(raw).hexdigest()
    LOGGER.info(
        "dxf_loaded extension=%s bytes=%d sha256=%s encoding=%s entities=%d texts=%d",
        source.suffix.casefold(), len(raw), fingerprint[:12], encoding, sum(counts.values()), len(texts),
    )
    return DxfLoadResult(source, fingerprint, len(raw), texts, lines, dict(counts), native_tables, warnings)
