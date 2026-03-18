#!/usr/bin/env python3
"""Normalize localization exports and sidecar metadata into one canonical snapshot."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALIAS_MAP = {
    "key": ["key", "name", "string_name"],
    "source_text": ["source_text", "source", "original_text", "english", "en", "原文"],
    "background": ["background", "context", "description", "scene", "背景说明", "场景"],
    "screen": ["screen", "page", "route", "页面"],
    "legacy_module": ["模块", "module"],
    "component": ["component", "ui_component", "控件"],
    "intent": ["intent", "purpose", "文案意图", "意图"],
    "screenshot_ref": ["screenshot_ref", "figma_ref", "截图", "示意图"],
    "extraction_mode": ["extraction_mode", "evidence_mode", "来源方式"],
    "evidence_confidence": ["evidence_confidence", "confidence", "证据置信度"],
    "length_limit": ["length_limit", "char_limit", "长度限制"],
    "message_format": ["message_format", "format", "消息格式"],
    "placeholders": ["placeholders", "variables", "占位符"],
    "risk_level": ["risk_level", "risk", "风险等级"],
    "owner": ["owner", "reviewer", "业务owner"],
    "status": ["status", "状态"],
    "updated_at": ["updated_at", "last_updated", "更新时间"],
}

IOS_LINE_RE = re.compile(
    r'^\s*"(?P<key>(?:\\.|[^"\\])*)"\s*=\s*"(?P<value>(?:\\.|[^"\\])*)"\s*;\s*$'
)
KV_SPEC_RE = re.compile(r"(?P<name>[a-z_]+)=(?P<value>.+)")

SINGLE_TOKEN_LOCALES = {
    "en": "en",
    "english": "en",
    "de": "de",
    "german": "de",
    "fr": "fr",
    "french": "fr",
    "it": "it",
    "italian": "it",
    "es": "es",
    "spanish": "es",
    "ru": "ru",
    "russian": "ru",
    "ko": "ko",
    "korean": "ko",
    "hi": "hi",
    "hindi": "hi",
}

ANDROID_QUALIFIER_LOCALES = {
    "zh-rcn": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-rtw": "zh-Hant",
    "zh-tw": "zh-Hant",
    "pt-rbr": "pt-BR",
    "pt-br": "pt-BR",
    "de": "de",
    "fr": "fr",
    "it": "it",
    "es": "es",
    "ru": "ru",
    "ko": "ko",
    "hi": "hi",
    "en": "en",
    "zh": "zh-Hans",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize exported localization files into a canonical snapshot JSON."
    )
    parser.add_argument(
        "--resource",
        action="append",
        default=[],
        help=(
            "Resource descriptor in key=value form, for example "
            "'kind=ios,path=./en.strings,locale=en,platform=ios'. "
            "Supported kinds: ios, android, json, csv."
        ),
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        default=[],
        help=(
            "Directory containing exported resources. The normalizer will auto-detect "
            "common iOS `.strings`, Android `strings.xml`, locale JSON, and CSV catalogs."
        ),
    )
    parser.add_argument(
        "--metadata",
        "--sidecar",
        action="append",
        default=[],
        help="Metadata sidecar path. Supported formats: .csv or .json.",
    )
    parser.add_argument(
        "--base-locale",
        default="en",
        help="Preferred source locale. Default: en",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the normalized snapshot JSON.",
    )
    return parser.parse_args()


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9]+", text.lower()) if token]


def detect_locale_from_tokens(tokens: list[str], default: str = "") -> str:
    for left, right, locale in (
        ("zh", "hans", "zh-Hans"),
        ("zh", "cn", "zh-Hans"),
        ("zh", "chs", "zh-Hans"),
        ("zh", "hant", "zh-Hant"),
        ("zh", "tw", "zh-Hant"),
        ("zh", "cht", "zh-Hant"),
        ("pt", "br", "pt-BR"),
    ):
        for index in range(len(tokens) - 1):
            if tokens[index] == left and tokens[index + 1] == right:
                return locale
    for token in tokens:
        locale = SINGLE_TOKEN_LOCALES.get(token)
        if locale:
            return locale
    return default


def detect_ios_locale(path: Path, base_locale: str) -> str:
    parent = path.parent.name
    if parent.lower().endswith(".lproj"):
        return parent[:-6] or base_locale
    return detect_locale_from_tokens(tokenize(path.stem), base_locale)


def detect_android_locale(path: Path, base_locale: str) -> str:
    parent = path.parent.name.lower()
    if parent == "values":
        return base_locale
    if parent.startswith("values-"):
        qualifier = parent[len("values-") :]
        locale = ANDROID_QUALIFIER_LOCALES.get(qualifier)
        if locale:
            return locale
        if qualifier.startswith("b+"):
            subtags = [part for part in qualifier[2:].split("+") if part]
            return detect_locale_from_tokens(subtags, base_locale)
        parts = [part[1:] if part.startswith("r") else part for part in qualifier.split("-")]
        return detect_locale_from_tokens(parts, base_locale)
    return detect_locale_from_tokens(tokenize(path.stem), base_locale)


def maybe_catalog_resource(path: Path, base_locale: str) -> dict[str, str] | None:
    stem_tokens = tokenize(path.stem)
    stem_text = path.stem.lower()
    if any(flag in stem_text for flag in ("context", "sidecar", "metadata", "template")):
        return None
    locale = detect_locale_from_tokens(stem_tokens, "")
    if path.suffix.lower() == ".json":
        if path.stem.lower() in {"manifest", "summary"}:
            return None
        if locale or "locale" in stem_text or "catalog" in stem_text:
            return {"kind": "json", "path": str(path), "locale": locale or base_locale, "platform": "json"}
        return None
    if path.suffix.lower() == ".csv":
        if locale or "locale" in stem_text or "catalog" in stem_text or "strings" in stem_text:
            return {"kind": "csv", "path": str(path), "locale": locale or base_locale, "platform": "csv"}
    return None


def discover_resource_specs(input_dirs: list[str], base_locale: str) -> list[dict[str, str]]:
    discovered: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for raw_dir in input_dirs:
        root = Path(raw_dir).expanduser()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Input directory does not exist or is not a directory: {root}")
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            spec: dict[str, str] | None = None
            suffix = path.suffix.lower()
            if suffix == ".strings":
                spec = {
                    "kind": "ios",
                    "path": str(path),
                    "locale": detect_ios_locale(path, base_locale),
                    "platform": "ios",
                }
            elif path.name == "strings.xml" or (suffix == ".xml" and "android" in path.stem.lower()):
                spec = {
                    "kind": "android",
                    "path": str(path),
                    "locale": detect_android_locale(path, base_locale),
                    "platform": "android",
                }
            else:
                spec = maybe_catalog_resource(path, base_locale)
            if not spec:
                continue
            normalized_path = str(Path(spec["path"]).expanduser())
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)
            discovered.append(spec)
    return discovered


def dedupe_resource_specs(resource_specs: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for spec in resource_specs:
        normalized_path = str(Path(spec["path"]).expanduser())
        if normalized_path in seen_paths:
            continue
        seen_paths.add(normalized_path)
        deduped.append(spec)
    return deduped


def parse_resource_spec(spec: str) -> dict[str, str]:
    parts = [part.strip() for part in spec.split(",") if part.strip()]
    parsed: dict[str, str] = {}
    for part in parts:
        match = KV_SPEC_RE.match(part)
        if not match:
            raise ValueError(f"Invalid resource descriptor segment: {part}")
        parsed[match.group("name")] = match.group("value")
    if "kind" not in parsed or "path" not in parsed:
        raise ValueError(f"Resource descriptor must include kind and path: {spec}")
    parsed.setdefault("locale", "")
    parsed.setdefault("platform", parsed["kind"])
    return parsed


def decode_ios_string(value: str) -> str:
    return bytes(value, "utf-8").decode("unicode_escape")


def parse_ios_strings(path: Path) -> OrderedDict[str, str]:
    entries: OrderedDict[str, str] = OrderedDict()
    for raw_line in load_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("/*"):
            continue
        match = IOS_LINE_RE.match(line)
        if not match:
            continue
        key = decode_ios_string(match.group("key"))
        value = decode_ios_string(match.group("value"))
        entries[key] = value
    return entries


def parse_android_xml(path: Path) -> OrderedDict[str, str]:
    tree = ET.parse(path)
    root = tree.getroot()
    entries: OrderedDict[str, str] = OrderedDict()
    for node in root.findall("string"):
        key = node.attrib.get("name")
        if not key:
            continue
        value = "".join(node.itertext()).strip()
        entries[key] = value
    return entries


def parse_json_resource(path: Path) -> OrderedDict[str, str]:
    data = json.loads(load_text(path))
    entries: OrderedDict[str, str] = OrderedDict()
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                entries[str(key)] = value
        return entries
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            value = item.get("value") or item.get("source_text")
            if key and isinstance(value, str):
                entries[str(key)] = value
    return entries


def parse_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_csv_resource(path: Path) -> OrderedDict[str, str]:
    entries: OrderedDict[str, str] = OrderedDict()
    for row in parse_csv_rows(path):
        normalized = normalize_row(row)
        key = normalized.get("key")
        value = normalized.get("source_text") or row.get("value")
        if key and isinstance(value, str):
            entries[str(key)] = value
    return entries


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    lowered = {
        str(key).strip().lower(): value
        for key, value in row.items()
        if key is not None and value not in (None, "")
    }
    normalized: dict[str, Any] = {}
    for target, aliases in ALIAS_MAP.items():
        for alias in aliases:
            if alias.lower() in lowered:
                normalized[target] = lowered[alias.lower()]
                break
    return normalized


def ensure_entry(bucket: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in bucket:
        bucket[key] = {
            "key": key,
            "source_locale": None,
            "source_text": None,
            "screen": None,
            "component": None,
            "intent": None,
            "background": None,
            "screenshot_ref": None,
            "length_limit": None,
            "message_format": "plain",
            "placeholders": [],
            "risk_level": None,
            "owner": None,
            "status": None,
            "updated_at": None,
            "source_evidence": {
                "extraction_mode": None,
                "confidence": None,
                "verified_text": None,
                "artifacts": [],
            },
            "translations": OrderedDict(),
            "origins": [],
            "issues": [],
        }
    return bucket[key]


def update_entry_from_translation(
    entry: dict[str, Any],
    locale: str,
    value: str,
    origin: dict[str, str],
    base_locale: str,
) -> None:
    if value is None:
        return
    entry["translations"][locale] = value
    entry["origins"].append(origin)
    source_evidence = entry.setdefault(
        "source_evidence",
        {"extraction_mode": None, "confidence": None, "verified_text": None, "artifacts": []},
    )
    artifacts = source_evidence.setdefault("artifacts", [])
    artifacts.append(
        {
            "kind": origin["kind"],
            "path": origin["path"],
            "locale": locale,
            "platform": origin["platform"],
        }
    )
    if source_evidence.get("extraction_mode") in (None, "", "user-transcribed"):
        source_evidence["extraction_mode"] = "snapshot-export"
    if source_evidence.get("confidence") in (None, ""):
        source_evidence["confidence"] = "high"
    if source_evidence.get("verified_text") is None:
        source_evidence["verified_text"] = True
    if locale == base_locale and not entry["source_text"]:
        entry["source_locale"] = locale
        entry["source_text"] = value
    elif not entry["source_text"] and not entry["source_locale"]:
        entry["source_locale"] = locale
        entry["source_text"] = value


def placeholder_from_name(name: str) -> dict[str, str]:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")
    if not cleaned:
        cleaned = "value"
    return {
        "name": cleaned,
        "type": "string",
        "canonical": f"{{{cleaned}}}",
        "web": f"{{{cleaned}}}",
    }


def parse_placeholders(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        parsed: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                spec = dict(item)
                spec.setdefault("canonical", f"{{{name}}}")
                spec.setdefault("web", spec["canonical"])
                parsed.append(spec)
            else:
                text = str(item).strip()
                if text:
                    parsed.append(placeholder_from_name(text))
        return parsed
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") or text.startswith("{"):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                decoded = None
            if decoded is not None:
                return parse_placeholders(decoded)
        separators = "|" if "|" in value else ","
        return [placeholder_from_name(item.strip()) for item in value.split(separators) if item.strip()]
    return [placeholder_from_name(str(value))]


def normalize_length_limit(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if text.isdigit():
        return {"mode": "strict", "max_chars": int(text)}
    match = re.match(r"^(strict|short|none)\s*[:=]?\s*(\d+)?$", text, re.IGNORECASE)
    if match:
        mode = match.group(1).lower()
        max_chars = int(match.group(2)) if match.group(2) else None
        payload: dict[str, Any] = {"mode": mode}
        if max_chars is not None:
            payload["max_chars"] = max_chars
        return payload
    return text


def merge_metadata(entry: dict[str, Any], row: dict[str, Any], metadata_origin: str) -> None:
    for field in ("screen", "component", "intent", "background", "screenshot_ref", "risk_level", "owner", "status", "updated_at"):
        value = row.get(field)
        if value not in (None, "") and not entry.get(field):
            entry[field] = value

    legacy_module = row.get("legacy_module")
    if legacy_module not in (None, "") and not entry.get("screen"):
        entry["screen"] = legacy_module
        entry["issues"].append(
            {
                "severity": "warning",
                "message": "module was used as a fallback screen hint; prefer a stable screen/page field",
                "module": legacy_module,
            }
        )

    message_format = row.get("message_format")
    if message_format not in (None, "") and entry.get("message_format") in (None, "", "plain"):
        entry["message_format"] = message_format

    if row.get("source_text") not in (None, ""):
        candidate = str(row["source_text"])
        if entry["source_text"] and entry["source_text"] != candidate:
            entry["issues"].append(
                {
                    "severity": "warning",
                    "message": "metadata source_text differs from resource text",
                    "metadata_source_text": candidate,
                }
            )
        else:
            entry["source_text"] = candidate

    if row.get("length_limit") not in (None, "") and not entry.get("length_limit"):
        entry["length_limit"] = normalize_length_limit(row["length_limit"])

    placeholders = parse_placeholders(row.get("placeholders"))
    if placeholders and not entry.get("placeholders"):
        entry["placeholders"] = placeholders
        if entry.get("message_format") in (None, "", "plain"):
            entry["message_format"] = "named-template"

    source_evidence = entry.setdefault(
        "source_evidence",
        {"extraction_mode": None, "confidence": None, "verified_text": None, "artifacts": []},
    )
    artifacts = source_evidence.setdefault("artifacts", [])
    artifact_descriptor: dict[str, Any] = {"kind": "metadata", "path": metadata_origin}
    if row.get("screenshot_ref") not in (None, ""):
        artifact_descriptor["screenshot_ref"] = row["screenshot_ref"]
    if artifact_descriptor not in artifacts:
        artifacts.append(artifact_descriptor)

    extraction_mode = row.get("extraction_mode")
    if extraction_mode not in (None, ""):
        source_evidence["extraction_mode"] = extraction_mode
    confidence = row.get("evidence_confidence")
    if confidence not in (None, ""):
        source_evidence["confidence"] = confidence

    if source_evidence.get("verified_text") is None:
        mode = str(source_evidence.get("extraction_mode") or "")
        source_evidence["verified_text"] = mode in {"snapshot-export", "pdf-text", "user-transcribed"}

    if row.get("source_text") not in (None, "") and not entry.get("origins"):
        if source_evidence.get("extraction_mode") in (None, ""):
            source_evidence["extraction_mode"] = "user-transcribed"
        if source_evidence.get("confidence") in (None, ""):
            source_evidence["confidence"] = "medium"
        source_evidence["verified_text"] = True


def load_metadata(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return [normalize_row(row) for row in parse_csv_rows(path)]
    if suffix == ".json":
        payload = json.loads(load_text(path))
        if isinstance(payload, list):
            return [normalize_row(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            if "entries" in payload and isinstance(payload["entries"], list):
                return [normalize_row(item) for item in payload["entries"] if isinstance(item, dict)]
            return [normalize_row(payload)]
    raise ValueError(f"Unsupported metadata format: {path}")


def parse_resource(spec: dict[str, str], base_locale: str) -> OrderedDict[str, str]:
    path = Path(spec["path"]).expanduser()
    kind = spec["kind"].lower()
    if kind == "ios":
        return parse_ios_strings(path)
    if kind == "android":
        return parse_android_xml(path)
    if kind == "json":
        return parse_json_resource(path)
    if kind == "csv":
        return parse_csv_resource(path)
    raise ValueError(f"Unsupported resource kind: {kind}")


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries: dict[str, Any] = {}
    resource_specs = [parse_resource_spec(spec) for spec in args.resource]
    resource_specs.extend(discover_resource_specs(args.input_dir, args.base_locale))
    resource_specs = dedupe_resource_specs(resource_specs)

    if not resource_specs and not args.metadata:
        raise SystemExit("Provide at least one --resource, --input-dir, or --metadata input.")

    for spec in resource_specs:
        locale = spec["locale"] or args.base_locale
        parsed_entries = parse_resource(spec, args.base_locale)
        for key, value in parsed_entries.items():
            entry = ensure_entry(entries, key)
            update_entry_from_translation(
                entry,
                locale=locale,
                value=value,
                origin={
                    "kind": spec["kind"],
                    "path": str(Path(spec["path"]).expanduser()),
                    "locale": locale,
                    "platform": spec["platform"],
                },
                base_locale=args.base_locale,
            )

    for metadata_path in args.metadata:
        path = Path(metadata_path).expanduser()
        rows = load_metadata(path)
        for row in rows:
            key = row.get("key")
            if not key:
                continue
            entry = ensure_entry(entries, str(key))
            merge_metadata(entry, row, str(path))

    ordered_entries = []
    for key in sorted(entries):
        entry = entries[key]
        source_evidence = entry.setdefault(
            "source_evidence",
            {"extraction_mode": None, "confidence": None, "verified_text": None, "artifacts": []},
        )
        if source_evidence.get("extraction_mode") in (None, ""):
            if entry.get("origins"):
                source_evidence["extraction_mode"] = "snapshot-export"
            elif entry.get("source_text"):
                source_evidence["extraction_mode"] = "user-transcribed"
        if source_evidence.get("confidence") in (None, ""):
            if source_evidence.get("extraction_mode") == "snapshot-export":
                source_evidence["confidence"] = "high"
            elif source_evidence.get("extraction_mode") == "user-transcribed":
                source_evidence["confidence"] = "medium"
        if source_evidence.get("verified_text") is None:
            source_evidence["verified_text"] = source_evidence.get("extraction_mode") in {
                "snapshot-export",
                "pdf-text",
                "user-transcribed",
            }
        if entry.get("placeholders") and entry.get("message_format") in (None, "", "plain"):
            entry["message_format"] = "named-template"
        if not entry["source_text"]:
            entry["issues"].append(
                {
                    "severity": "warning",
                    "message": "source_text is missing; review before reuse or translation",
                }
            )
        if not entry["screen"] or not entry["intent"] or not entry["background"]:
            entry["issues"].append(
                {
                    "severity": "warning",
                    "message": "context is incomplete; operate in downgraded mode or request more detail",
                }
            )
        ordered_entries.append(entry)

    payload = {
        "snapshot_version": "1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "base_locale": args.base_locale,
        "inputs": {
            "resources": resource_specs,
            "input_dirs": [str(Path(item).expanduser()) for item in args.input_dir],
            "metadata": [str(Path(item).expanduser()) for item in args.metadata],
        },
        "entries": ordered_entries,
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote normalized snapshot to {output_path}")
    print(f"Entries: {len(ordered_entries)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
