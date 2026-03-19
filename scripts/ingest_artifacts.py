#!/usr/bin/env python3
"""Ingest raw PRD artifacts into one evidence package."""

from __future__ import annotations

import argparse
import csv
import json
import quopri
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
import xml.etree.ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SS_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

NS = {
    "w": W_NS,
    "r": R_NS,
    "rel": PKG_REL_NS,
    "ss": SS_NS,
    "a": A_NS,
}

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".html", ".htm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | IMAGE_SUFFIXES | {".csv", ".json", ".docx", ".doc", ".rtf", ".xlsx", ".pdf", ".mhtml"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest raw PRD artifacts into a canonical evidence package.")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Files or directories containing PRD artifacts such as Markdown, HTML, MHTML, Word, PDF, XLSX, CSV, JSON, or screenshots.",
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        default=[],
        help="Directory containing mixed artifacts. May be passed multiple times.",
    )
    parser.add_argument(
        "--source-locale",
        default="en",
        help="Source locale for extracted copy. Default: en",
    )
    parser.add_argument("--output", required=True, help="Output path for the evidence package JSON.")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def command_output(*args: str) -> str:
    try:
        result = subprocess.run(
            list(args),
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def discover_paths(inputs: list[str], input_dirs: list[str]) -> list[Path]:
    candidates = [Path(value).expanduser() for value in [*inputs, *input_dirs]]
    discovered: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.exists():
            continue
        if candidate.is_dir():
            files = sorted(item for item in candidate.rglob("*") if item.is_file())
        else:
            files = [candidate]
        for path in files:
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            normalized = str(path.resolve())
            if normalized in seen:
                continue
            seen.add(normalized)
            discovered.append(path)
    return discovered


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [block.strip() for block in re.split(r"\n\s*\n+", normalized) if block.strip()]


def tokenize_filename(path: Path) -> list[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9]+", path.stem.lower()) if token]


def source_confidence(kind: str) -> str:
    if kind in {"markdown", "text", "html", "mhtml", "csv", "json", "docx", "doc", "rtf", "xlsx"}:
        return "high"
    if kind == "pdf":
        return "medium"
    return "low"


def extraction_mode(kind: str, has_text: bool) -> str:
    if kind == "pdf":
        return "pdf-text" if has_text else "vision"
    if kind in {"image", "figma-image"}:
        return "vision"
    return "structured-text"


def normalize_block_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def build_text_block(
    artifact_id: str,
    index: int,
    block_type: str,
    text: str,
    location: dict[str, Any] | None = None,
    fields: dict[str, Any] | None = None,
    image_refs: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "block_id": f"{artifact_id}:block:{index}",
        "type": block_type,
        "text": normalize_block_text(text),
        "location": location or {},
        "image_refs": image_refs or [],
    }
    if fields:
        payload["fields"] = fields
    if metadata:
        payload["metadata"] = metadata
    return payload


def decode_text_bytes(payload: bytes, preferred_charset: str | None = None) -> str:
    charsets = [preferred_charset, "utf-8", "utf-8-sig", "gb18030", "gbk", "big5"]
    for charset in charsets:
        if not charset:
            continue
        try:
            return payload.decode(charset)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


class HTMLToMarkdownishParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "section", "article", "blockquote", "pre"}
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.lines: list[str] = []
        self.block_buffer: list[str] = []
        self.list_prefix = ""
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None
        self.current_row_is_header = False

    def flush_block(self) -> None:
        text = normalize_block_text(" ".join(self.block_buffer))
        if text:
            self.lines.append(f"{self.list_prefix}{text}".strip())
        self.block_buffer = []
        self.list_prefix = ""

    def flush_row(self) -> None:
        if self.current_row and any(cell.strip() for cell in self.current_row):
            rendered = [cell if cell else " " for cell in self.current_row]
            self.lines.append("| " + " | ".join(rendered) + " |")
            if self.current_row_is_header:
                self.lines.append("| " + " | ".join("---" for _ in rendered) + " |")
        self.current_row = None
        self.current_row_is_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        attributes = dict(attrs)
        if tag in self.BLOCK_TAGS or tag in self.HEADING_TAGS:
            self.flush_block()
        elif tag == "li":
            self.flush_block()
            self.list_prefix = "- "
        elif tag == "br":
            self.flush_block()
        elif tag == "tr":
            self.flush_block()
            self.current_row = []
            self.current_row_is_header = False
        elif tag in {"td", "th"}:
            self.current_cell = []
            if tag == "th":
                self.current_row_is_header = True
        elif tag == "img":
            self.flush_block()
            alt = normalize_block_text(attributes.get("alt") or "image")
            src = normalize_block_text(attributes.get("src") or "embedded-image")
            self.lines.append(f"![{alt}]({src})")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in self.BLOCK_TAGS or tag in self.HEADING_TAGS or tag == "li":
            self.flush_block()
        elif tag in {"td", "th"} and self.current_row is not None and self.current_cell is not None:
            self.current_row.append(normalize_block_text(" ".join(self.current_cell)))
            self.current_cell = None
        elif tag == "tr":
            self.flush_row()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = normalize_block_text(data)
        if not text:
            return
        if self.current_row is not None and self.current_cell is not None:
            self.current_cell.append(text)
        else:
            self.block_buffer.append(text)

    def render(self) -> str:
        self.flush_block()
        self.flush_row()
        return "\n".join(self.lines) + ("\n" if self.lines else "")


def html_like_to_markdownish(text: str) -> str:
    parser = HTMLToMarkdownishParser()
    parser.feed(text)
    parser.close()
    return parser.render()


def parse_markdown_text(text: str, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    paragraph_buffer: list[str] = []
    paragraph_start = 0
    table_lines: list[str] = []
    table_start = 0

    def flush_paragraph() -> None:
        nonlocal index, paragraph_buffer, paragraph_start
        if not paragraph_buffer:
            return
        paragraph_text = normalize_block_text(" ".join(paragraph_buffer))
        if paragraph_text:
            blocks.append(
                build_text_block(
                    artifact_id,
                    index,
                    "paragraph",
                    paragraph_text,
                    location={"line_start": paragraph_start + 1},
                )
            )
            index += 1
        paragraph_buffer = []

    def flush_table() -> None:
        nonlocal index, table_lines, table_start
        if len(table_lines) < 2:
            table_lines = []
            return
        parsed = parse_markdown_table(table_lines)
        for offset, row in enumerate(parsed):
            blocks.append(
                build_text_block(
                    artifact_id,
                    index,
                    "table-row",
                    " | ".join(str(value) for value in row.values() if str(value).strip()),
                    location={"line_start": table_start + 1 + offset + 1},
                    fields=row,
                )
            )
            index += 1
        table_lines = []

    for line_number, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            if not table_lines:
                table_start = line_number
            table_lines.append(stripped)
            continue
        flush_table()

        image_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", raw_line)
        if image_match:
            flush_paragraph()
            image_path = image_match.group(1).strip()
            images.append(
                {
                    "image_id": f"{artifact_id}:image:{len(images)}",
                    "ref": image_path,
                    "location": {"line_start": line_number + 1},
                    "level": "screen",
                }
            )
            continue
        if not stripped:
            flush_paragraph()
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            blocks.append(
                build_text_block(
                    artifact_id,
                    index,
                    "heading",
                    heading_match.group(2),
                    location={"line_start": line_number + 1},
                    metadata={"level": len(heading_match.group(1))},
                )
            )
            index += 1
            continue
        if stripped.startswith(("- ", "* ", "+ ")):
            flush_paragraph()
            blocks.append(
                build_text_block(
                    artifact_id,
                    index,
                    "list-item",
                    stripped[2:].strip(),
                    location={"line_start": line_number + 1},
                )
            )
            index += 1
            continue
        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            blocks.append(
                build_text_block(
                    artifact_id,
                    index,
                    "list-item",
                    re.sub(r"^\d+\.\s+", "", stripped),
                    location={"line_start": line_number + 1},
                )
            )
            index += 1
            continue
        if not paragraph_buffer:
            paragraph_start = line_number
        paragraph_buffer.append(stripped)

    flush_paragraph()
    flush_table()
    return blocks, images


def parse_markdown_or_text(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return parse_markdown_text(load_text(path), artifact_id)


def parse_html_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    html_text = decode_text_bytes(path.read_bytes())
    return parse_markdown_text(html_like_to_markdownish(html_text), artifact_id)


def parse_mhtml_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    html_payload: bytes | None = None
    charset: str | None = None
    notes: list[str] = []
    for part in msg.walk():
        if part.get_content_type() != "text/html":
            continue
        html_payload = part.get_payload(decode=True)
        if html_payload is None:
            raw_payload = part.get_payload()
            if isinstance(raw_payload, str):
                html_payload = quopri.decodestring(raw_payload.encode("utf-8", errors="ignore"))
        charset = part.get_content_charset()
        break
    if not html_payload:
        notes.append("no html part found in mhtml payload")
        return [], [], notes
    html_text = decode_text_bytes(html_payload, charset)
    if "�" in html_text:
        notes.append("html body contained replacement characters after decode")
    return (*parse_markdown_text(html_like_to_markdownish(html_text), artifact_id), notes)


def parse_markdown_table(lines: list[str]) -> list[dict[str, str]]:
    if len(lines) < 2:
        return []
    header_cells = split_table_row(lines[0])
    separator_cells = split_table_row(lines[1])
    if len(header_cells) != len(separator_cells):
        return []
    rows: list[dict[str, str]] = []
    for raw_row in lines[2:]:
        cells = split_table_row(raw_row)
        if len(cells) != len(header_cells):
            continue
        rows.append({header_cells[index]: cells[index] for index in range(len(header_cells))})
    return rows


def split_table_row(value: str) -> list[str]:
    trimmed = value.strip().strip("|")
    return [cell.strip() for cell in trimmed.split("|")]


def parse_csv_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            text = " | ".join(str(value).strip() for value in row.values() if str(value).strip())
            if not text:
                continue
            blocks.append(
                build_text_block(
                    artifact_id,
                    index,
                    "table-row",
                    text,
                    location={"row": index + 2},
                    fields={str(key): value for key, value in row.items() if key is not None},
                )
            )
    return blocks, []


def parse_json_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(load_text(path))
    blocks: list[dict[str, Any]] = []
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        payload = payload["entries"]
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            if isinstance(item, dict):
                text = " | ".join(str(value).strip() for value in item.values() if isinstance(value, (str, int, float)) and str(value).strip())
                if not text:
                    continue
                blocks.append(
                    build_text_block(
                        artifact_id,
                        index,
                        "json-entry",
                        text,
                        location={"index": index},
                        fields={str(key): value for key, value in item.items()},
                    )
                )
        return blocks, []
    if isinstance(payload, dict):
        index = 0
        for key, value in payload.items():
            if isinstance(value, str) and value.strip():
                blocks.append(
                    build_text_block(
                        artifact_id,
                        index,
                        "json-entry",
                        value,
                        location={"key": str(key)},
                        fields={"key": key, "value": value},
                    )
                )
                index += 1
    return blocks, []


def parse_docx_relationships(package: zipfile.ZipFile) -> dict[str, str]:
    rel_path = "word/_rels/document.xml.rels"
    if rel_path not in package.namelist():
        return {}
    root = ET.fromstring(package.read(rel_path))
    mapping: dict[str, str] = {}
    for node in root.findall("rel:Relationship", NS):
        rel_id = node.attrib.get("Id")
        target = node.attrib.get("Target")
        if rel_id and target:
            mapping[rel_id] = str(PurePosixPath("word") / PurePosixPath(target))
    return mapping


def text_from_docx_node(node: ET.Element) -> str:
    return normalize_block_text("".join(text or "" for text in node.itertext()))


def image_refs_from_docx_node(node: ET.Element, rels: dict[str, str]) -> list[str]:
    refs: list[str] = []
    for descendant in node.iter():
        embed = descendant.attrib.get(f"{{{R_NS}}}embed")
        if embed and embed in rels and rels[embed] not in refs:
            refs.append(rels[embed])
    return refs


def parse_docx_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as package:
        rels = parse_docx_relationships(package)
        document_root = ET.fromstring(package.read("word/document.xml"))
        body = document_root.find("w:body", NS)
        if body is None:
            return blocks, images
        block_index = 0
        for order, child in enumerate(list(body)):
            tag = child.tag.split("}")[-1]
            if tag == "p":
                text = text_from_docx_node(child)
                refs = image_refs_from_docx_node(child, rels)
                style = ""
                style_node = child.find("w:pPr/w:pStyle", NS)
                if style_node is not None:
                    style = style_node.attrib.get(f"{{{W_NS}}}val", "")
                if refs:
                    for ref in refs:
                        images.append(
                            {
                                "image_id": f"{artifact_id}:image:{len(images)}",
                                "ref": ref,
                                "location": {"order": order},
                                "level": "screen",
                            }
                        )
                if text or refs:
                    block_type = "heading" if style.lower().startswith("heading") else "paragraph"
                    blocks.append(
                        build_text_block(
                            artifact_id,
                            block_index,
                            block_type,
                            text,
                            location={"order": order},
                            image_refs=refs,
                            metadata={"style": style} if style else None,
                        )
                    )
                    block_index += 1
            elif tag == "tbl":
                rows = child.findall("w:tr", NS)
                header_values: list[str] | None = None
                for row_index, row in enumerate(rows):
                    cells = [text_from_docx_node(cell) for cell in row.findall("w:tc", NS)]
                    if not any(cells):
                        continue
                    refs = image_refs_from_docx_node(row, rels)
                    if row_index == 0 and looks_like_header_row(cells):
                        header_values = cells
                        continue
                    fields = None
                    if header_values and len(header_values) == len(cells):
                        fields = {
                            header_values[index]: cells[index]
                            for index in range(len(cells))
                            if header_values[index].strip()
                        }
                    blocks.append(
                        build_text_block(
                            artifact_id,
                            block_index,
                            "table-row",
                            " | ".join(value for value in cells if value),
                            location={"order": order, "row": row_index + 1},
                            fields=fields,
                            image_refs=refs,
                        )
                    )
                    block_index += 1
                    for ref in refs:
                        images.append(
                            {
                                "image_id": f"{artifact_id}:image:{len(images)}",
                                "ref": ref,
                                "location": {"order": order, "row": row_index + 1},
                                "level": "screen",
                            }
                        )
    return blocks, images


def extract_via_textutil(path: Path) -> str:
    return command_output("/usr/bin/textutil", "-convert", "txt", "-stdout", str(path))


def parse_legacy_office_text(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = extract_via_textutil(path)
    if not text:
        return [], []
    return parse_text_content(text, artifact_id)


def parse_text_content(text: str, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    for index, paragraph in enumerate(split_paragraphs(text)):
        block_type = "heading" if len(paragraph) < 80 and paragraph == paragraph.strip() and "\n" not in paragraph else "paragraph"
        blocks.append(build_text_block(artifact_id, index, block_type, paragraph, location={"index": index}))
    return blocks, []


def parse_shared_strings(package: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in package.namelist():
        return []
    root = ET.fromstring(package.read(path))
    values: list[str] = []
    for node in root.findall("ss:si", NS):
        values.append(normalize_block_text("".join(text or "" for text in node.itertext())))
    return values


def parse_sheet_names(package: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook_root = ET.fromstring(package.read("xl/workbook.xml"))
    rel_root = ET.fromstring(package.read("xl/_rels/workbook.xml.rels"))
    rels = {
        node.attrib.get("Id"): node.attrib.get("Target")
        for node in rel_root.findall("rel:Relationship", NS)
        if node.attrib.get("Id") and node.attrib.get("Target")
    }
    sheets: list[tuple[str, str]] = []
    for sheet in workbook_root.findall("ss:sheets/ss:sheet", NS):
        name = sheet.attrib.get("name") or "Sheet"
        rel_id = sheet.attrib.get(f"{{{R_NS}}}id")
        target = rels.get(rel_id or "")
        if target:
            sheets.append((name, str(PurePosixPath("xl") / PurePosixPath(target))))
    return sheets


def parse_xlsx_drawings(package: zipfile.ZipFile, sheet_path: str) -> dict[int, list[str]]:
    rel_path = str(PurePosixPath(sheet_path).parent / "_rels" / (PurePosixPath(sheet_path).name + ".rels"))
    if rel_path not in package.namelist():
        return {}
    sheet_rels_root = ET.fromstring(package.read(rel_path))
    rels = {
        node.attrib.get("Id"): node.attrib.get("Target")
        for node in sheet_rels_root.findall("rel:Relationship", NS)
        if node.attrib.get("Id") and node.attrib.get("Target")
    }
    drawing_target = ""
    for rel_id, target in rels.items():
        if "drawing" in target:
            drawing_target = str(PurePosixPath(sheet_path).parent / PurePosixPath(target))
            break
    if not drawing_target or drawing_target not in package.namelist():
        return {}

    drawing_rel_path = str(PurePosixPath(drawing_target).parent / "_rels" / (PurePosixPath(drawing_target).name + ".rels"))
    drawing_rels: dict[str, str] = {}
    if drawing_rel_path in package.namelist():
        drawing_rel_root = ET.fromstring(package.read(drawing_rel_path))
        drawing_rels = {
            node.attrib.get("Id"): node.attrib.get("Target")
            for node in drawing_rel_root.findall("rel:Relationship", NS)
            if node.attrib.get("Id") and node.attrib.get("Target")
        }

    drawing_root = ET.fromstring(package.read(drawing_target))
    anchors: dict[int, list[str]] = {}
    for anchor in drawing_root:
        row_node = anchor.find("./xdr:from/xdr:row", {"xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"})
        blip = anchor.find(".//a:blip", NS)
        if row_node is None or blip is None:
            continue
        rel_id = blip.attrib.get(f"{{{R_NS}}}embed")
        target = drawing_rels.get(rel_id or "")
        if not target:
            continue
        row_index = int(row_node.text or "0") + 1
        image_path = str(PurePosixPath("xl") / PurePosixPath("drawings") / PurePosixPath(target))
        anchors.setdefault(row_index, []).append(image_path)
    return anchors


def column_letters(cell_ref: str) -> str:
    match = re.match(r"([A-Z]+)", cell_ref or "")
    return match.group(1) if match else ""


def parse_xlsx_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as package:
        shared_strings = parse_shared_strings(package)
        sheets = parse_sheet_names(package)
        block_index = 0
        for sheet_name, sheet_path in sheets:
            sheet_root = ET.fromstring(package.read(sheet_path))
            image_rows = parse_xlsx_drawings(package, sheet_path)
            for row_idx, refs in image_rows.items():
                for ref in refs:
                    images.append(
                        {
                            "image_id": f"{artifact_id}:image:{len(images)}",
                            "ref": ref,
                            "location": {"sheet": sheet_name, "row": row_idx},
                            "level": "screen",
                        }
                    )
            rows: list[tuple[int, dict[str, str]]] = []
            for row in sheet_root.findall(".//ss:sheetData/ss:row", NS):
                row_number = int(row.attrib.get("r", "0"))
                cells: dict[str, str] = {}
                for cell in row.findall("ss:c", NS):
                    cell_ref = cell.attrib.get("r", "")
                    column = column_letters(cell_ref)
                    cell_type = cell.attrib.get("t", "")
                    value = ""
                    if cell_type == "inlineStr":
                        value = normalize_block_text("".join(text or "" for text in cell.itertext()))
                    else:
                        value_node = cell.find("ss:v", NS)
                        if value_node is None or value_node.text is None:
                            continue
                        raw_value = value_node.text
                        if cell_type == "s" and raw_value.isdigit():
                            index = int(raw_value)
                            if 0 <= index < len(shared_strings):
                                value = shared_strings[index]
                        else:
                            value = raw_value
                    if value.strip():
                        cells[column] = normalize_block_text(value)
                if cells:
                    rows.append((row_number, cells))
            header_map: list[str] | None = None
            if rows and looks_like_header_row(list(rows[0][1].values())):
                header_map = [value for _, value in sorted(rows[0][1].items())]
                rows = rows[1:]
            for row_number, cells in rows:
                ordered_values = [value for _, value in sorted(cells.items())]
                fields = None
                if header_map and len(header_map) == len(ordered_values):
                    fields = {
                        header_map[index]: ordered_values[index]
                        for index in range(len(ordered_values))
                        if header_map[index].strip()
                    }
                refs = image_rows.get(row_number, [])
                blocks.append(
                    build_text_block(
                        artifact_id,
                        block_index,
                        "sheet-row",
                        " | ".join(ordered_values),
                        location={"sheet": sheet_name, "row": row_number},
                        fields=fields,
                        image_refs=refs,
                    )
                )
                block_index += 1
    return blocks, images


def looks_like_header_row(values: list[str]) -> bool:
    cleaned = [normalize_block_text(value) for value in values if normalize_block_text(value)]
    if len(cleaned) < 2:
        return False
    shortish = sum(1 for value in cleaned if len(value) <= 24)
    alpha_like = sum(1 for value in cleaned if re.search(r"[A-Za-z\u4e00-\u9fff]", value))
    return shortish == len(cleaned) and alpha_like == len(cleaned)


def parse_pdf_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    text = ""
    extraction = "vision"
    notes: list[str] = []

    pdftotext_output = command_output("pdftotext", "-layout", "-nopgbrk", str(path), "-")
    if pdftotext_output:
        text = pdftotext_output
        extraction = "pdf-text"
        notes.append("extracted with pdftotext")
    else:
        mdls_output = command_output("/usr/bin/mdls", "-raw", "-name", "kMDItemTextContent", str(path))
        if mdls_output and mdls_output not in {"(null)", '""'}:
            text = mdls_output.strip('"')
            extraction = "pdf-text"
            notes.append("extracted with mdls metadata text content")
        else:
            notes.append("no reliable local PDF text extractor available")

    blocks, images = parse_text_content(text, artifact_id) if text else ([], [])
    metadata = {"extraction_mode": extraction, "notes": notes}
    return blocks, images, metadata


def parse_image_artifact(path: Path, artifact_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return [], [{"image_id": f"{artifact_id}:image:0", "ref": str(path), "location": {}, "level": "screen"}]


def ingest_one(path: Path, artifact_index: int) -> dict[str, Any]:
    suffix = path.suffix.lower()
    artifact_id = f"artifact:{artifact_index}"
    kind = "text"
    notes: list[str] = []

    if suffix in {".md", ".markdown"}:
        kind = "markdown"
        blocks, images = parse_markdown_or_text(path, artifact_id)
    elif suffix in {".html", ".htm"}:
        kind = "html"
        blocks, images = parse_html_artifact(path, artifact_id)
    elif suffix == ".mhtml":
        kind = "mhtml"
        blocks, images, mhtml_notes = parse_mhtml_artifact(path, artifact_id)
        notes.extend(mhtml_notes)
    elif suffix == ".txt":
        kind = "text"
        blocks, images = parse_markdown_or_text(path, artifact_id)
    elif suffix == ".csv":
        kind = "csv"
        blocks, images = parse_csv_artifact(path, artifact_id)
    elif suffix == ".json":
        kind = "json"
        blocks, images = parse_json_artifact(path, artifact_id)
    elif suffix == ".docx":
        kind = "docx"
        blocks, images = parse_docx_artifact(path, artifact_id)
    elif suffix in {".doc", ".rtf"}:
        kind = suffix[1:]
        blocks, images = parse_legacy_office_text(path, artifact_id)
        if not blocks:
            notes.append("textutil could not extract reliable text")
    elif suffix == ".xlsx":
        kind = "xlsx"
        blocks, images = parse_xlsx_artifact(path, artifact_id)
    elif suffix == ".pdf":
        kind = "pdf"
        blocks, images, metadata = parse_pdf_artifact(path, artifact_id)
        notes.extend(metadata.get("notes", []))
    elif suffix in IMAGE_SUFFIXES:
        kind = "image"
        blocks, images = parse_image_artifact(path, artifact_id)
    else:
        kind = "unknown"
        blocks, images = [], []

    has_text = any(block.get("text") for block in blocks)
    payload: dict[str, Any] = {
        "artifact_id": artifact_id,
        "path": str(path.resolve()),
        "kind": kind,
        "source_confidence": source_confidence(kind),
        "extraction_mode": extraction_mode(kind, has_text),
        "text_available": has_text,
        "blocks": blocks,
        "images": images,
    }
    if notes:
        payload["notes"] = notes
    return payload


def build_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_count": len(artifacts),
        "text_artifacts": sum(1 for artifact in artifacts if artifact.get("text_available")),
        "image_artifacts": sum(1 for artifact in artifacts if artifact.get("images")),
        "block_count": sum(len(artifact.get("blocks", [])) for artifact in artifacts),
        "image_count": sum(len(artifact.get("images", [])) for artifact in artifacts),
    }


def main() -> int:
    args = parse_args()
    paths = discover_paths(args.inputs, args.input_dir)
    evidence = {
        "schema_version": "1.0",
        "created_at": now_iso(),
        "source_locale": args.source_locale,
        "artifacts": [ingest_one(path, index) for index, path in enumerate(paths)],
    }
    evidence["summary"] = build_summary(evidence["artifacts"])

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote evidence package to {output_path}")
    print(json.dumps(evidence["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
