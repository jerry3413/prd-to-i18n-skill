#!/usr/bin/env python3
"""Build a canonical manifest skeleton from a snapshot, copy-candidates package, or flat copy list."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AMBIGUOUS_LABELS = {"open", "continue", "done", "photos", "next", "back", "close"}
GENERIC_COMPONENTS = {"copy", "label", "text", "message"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a canonical manifest skeleton.")
    parser.add_argument("source", help="Path to a normalized snapshot JSON, a copy-candidates JSON package, or a flat CSV/JSON copy list.")
    parser.add_argument("--output", required=True, help="Output path for the manifest JSON.")
    parser.add_argument(
        "--task-mode",
        choices=["new-build", "change-sync", "dedupe", "translation-fix", "export-only"],
        default="new-build",
        help="Primary task mode. Default: new-build",
    )
    parser.add_argument(
        "--key-mode",
        choices=["auto", "inherit", "template", "canonical"],
        default="auto",
        help="Key strategy. Default: auto",
    )
    parser.add_argument("--surface", default="app", help="Surface prefix for canonical keys. Default: app")
    parser.add_argument(
        "--target-locales",
        default="en,zh-Hans",
        help="Comma-separated locale list required for delivery. Default: en,zh-Hans",
    )
    parser.add_argument(
        "--target-outputs",
        default="manifest,csv,json,ios,android",
        help="Comma-separated output formats. Default: manifest,csv,json,ios,android",
    )
    parser.add_argument(
        "--included-surfaces",
        help="Optional comma-separated list of surfaces included in this delivery, such as app,web,seller,backend-admin.",
    )
    parser.add_argument(
        "--required-locale-coverage",
        help="Optional comma-separated locale list that must be populated before export. Defaults to target-locales.",
    )
    parser.add_argument(
        "--max-entries-per-slice",
        type=int,
        default=50,
        help="Maximum entries per parallel slice. Default: 50",
    )
    parser.add_argument(
        "--revision-loop-limit",
        type=int,
        default=2,
        help="Maximum reviewer->translator revision loops. Default: 2",
    )
    return parser.parse_args()


def parse_list(value: str) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def slugify(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or fallback


def canonicalize_surface(value: str) -> str:
    lowered = str(value or "").strip().lower()
    if not lowered:
        return ""
    if any(token in lowered for token in ["frontend", "front-end", "front_end", "前端", "app", "mobile", "client", "ios", "android", "用户端"]):
        return "app"
    if any(token in lowered for token in ["web", "h5", "site", "pc"]):
        return "web"
    if any(token in lowered for token in ["seller", "merchant", "商家"]):
        return "seller"
    if any(token in lowered for token in ["backend", "backoffice", "back-office", "admin", "后台", "运营", "cms", "ops", "operation"]):
        return "backend-admin"
    if any(token in lowered for token in ["support", "客服"]):
        return "support"
    if any(token in lowered for token in ["internal", "内部", "tool", "工具"]):
        return "internal-tool"
    return slugify(lowered, "unknown_surface")


def source_locale_from_payload(payload: dict[str, Any]) -> str:
    locale = str(payload.get("base_locale") or payload.get("source_locale") or "en").strip()
    return locale or "en"


def normalize_rows_from_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_source(path: Path) -> tuple[str, list[dict[str, Any]]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "flat", normalize_rows_from_csv(path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return "snapshot", payload["entries"]
    if isinstance(payload, list):
        return "flat", [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return "flat", [payload]
    raise ValueError(f"Unsupported source payload: {path}")


def derive_intent(entry: dict[str, Any]) -> str:
    raw = str(entry.get("intent") or "").strip()
    if raw:
        return slugify(raw, "copy")
    source_text = str(entry.get("source_text") or "").strip()
    tokens = [token for token in re.findall(r"[a-zA-Z0-9]+", source_text.lower()) if token]
    return slugify("_".join(tokens[:4]), "copy")


def infer_change_level(entry: dict[str, Any], task_mode: str) -> str | None:
    existing = str(entry.get("change_level") or "").strip().upper()
    if existing:
        return existing
    if task_mode == "new-build":
        return "L3"
    if task_mode == "translation-fix":
        return "L1"
    return None


def infer_key_mode(raw_entries: list[dict[str, Any]], requested: str) -> str:
    if requested != "auto":
        return requested
    if raw_entries and all(str(entry.get("key") or "").strip() for entry in raw_entries):
        return "inherit"
    return "canonical"


def canonical_candidate(entry: dict[str, Any], surface: str) -> str:
    screen = slugify(str(entry.get("screen") or ""), "unknown_screen")
    component = slugify(str(entry.get("component") or ""), "copy")
    intent = derive_intent(entry)
    candidate = f"{slugify(surface, 'app')}_{screen}_{component}_{intent}"
    return re.sub(r"_+", "_", candidate)


def ambiguous_context(entry: dict[str, Any]) -> bool:
    text = str(entry.get("source_text") or "").strip().lower()
    background = str(entry.get("background") or "").strip()
    intent = str(entry.get("intent") or "").strip()
    if not text:
        return False
    if text in AMBIGUOUS_LABELS and (not background or not intent):
        return True
    if len(text.split()) <= 2 and (not background or not intent):
        return True
    return False


def build_pending_translations(
    existing: dict[str, Any],
    source_locale: str,
    target_locales: list[str],
    source_text: str,
) -> dict[str, Any]:
    translations = dict(existing) if isinstance(existing, dict) else {}
    source_value = translations.get(source_locale)
    if not isinstance(source_value, dict):
        source_value = {"value": source_text, "status": "source"}
    else:
        source_value.setdefault("value", source_text)
        source_value.setdefault("status", "source")
    translations[source_locale] = source_value

    for locale in target_locales:
        if locale == source_locale:
            continue
        value = translations.get(locale)
        if isinstance(value, dict):
            value.setdefault("status", "pending")
            value.setdefault("value", "")
        elif isinstance(value, str):
            translations[locale] = {"value": value, "status": "draft"}
        else:
            translations[locale] = {"value": "", "status": "pending"}
    return translations


def infer_human_review_required(
    entry: dict[str, Any],
) -> bool:
    risk = str(entry.get("risk_level") or "").lower()
    change_level = str(entry.get("change_level") or "").upper()
    existing_match = entry.get("existing_match")
    match_status = str(existing_match.get("status") or "").lower() if isinstance(existing_match, dict) else ""
    source_evidence = entry.get("source_evidence")
    confidence = ""
    if isinstance(source_evidence, dict):
        confidence = str(source_evidence.get("confidence") or "").lower()
    if risk == "high":
        return True
    if change_level in {"L2", "L3"}:
        return True
    if match_status in {"fuzzy", "ambiguous", "conflict"}:
        return True
    if confidence == "low" and risk in {"medium", "high"}:
        return True
    if ambiguous_context(entry):
        return True
    return False


def ensure_platform_outputs(outputs: list[str]) -> list[str]:
    allowed = {"manifest", "csv", "json", "ios", "android"}
    return [item for item in outputs if item in allowed] or ["manifest", "csv", "json", "ios", "android"]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source_path = Path(args.source).expanduser()
    source_kind, raw_entries = load_source(source_path)

    source_payload = None
    if source_kind == "snapshot":
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    source_locale = source_locale_from_payload(source_payload or {})
    target_locales = parse_list(args.target_locales)
    if source_locale not in target_locales:
        target_locales = [source_locale, *target_locales]
    required_locale_coverage = parse_list(args.required_locale_coverage) if args.required_locale_coverage else list(target_locales)
    key_mode = infer_key_mode(raw_entries, args.key_mode)
    target_outputs = ensure_platform_outputs(parse_list(args.target_outputs))
    detected_surfaces = [
        surface
        for surface in dict.fromkeys(
            canonicalize_surface(entry.get("surface"))
            for entry in raw_entries
            if isinstance(entry, dict) and canonicalize_surface(entry.get("surface"))
        )
        if surface
    ]
    inherited_included = parse_list(source_payload.get("included_surfaces")) if isinstance(source_payload, dict) else []
    included_surfaces = [
        canonicalize_surface(surface)
        for surface in (parse_list(args.included_surfaces) if args.included_surfaces else inherited_included)
        if canonicalize_surface(surface)
    ]
    if not included_surfaces:
        included_surfaces = list(detected_surfaces)

    entries: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            continue
        source_text = str(raw_entry.get("source_text") or "").strip()
        if not source_text:
            continue

        entry = dict(raw_entry)
        entry_surface = canonicalize_surface(entry.get("surface") or args.surface)
        entry["surface"] = entry_surface
        if included_surfaces and entry_surface and entry_surface not in included_surfaces:
            continue
        entry.setdefault("source_evidence", {"extraction_mode": "user-transcribed", "confidence": "medium", "verified_text": True, "artifacts": []})
        entry.setdefault("existing_match", {"status": "none", "matched_key": None, "confidence": 0.0})
        entry["change_level"] = infer_change_level(entry, args.task_mode)

        if key_mode == "inherit":
            key = str(entry.get("key") or "").strip()
            if not key:
                key = canonical_candidate(entry, args.surface)
            entry["key_candidate"] = key
            entry["key"] = key
        else:
            candidate = canonical_candidate(entry, args.surface)
            entry["key_candidate"] = candidate
            existing_key = str(entry.get("key") or "").strip()
            entry["key"] = candidate if key_mode == "canonical" or not existing_key else existing_key

        unique_key = entry["key"]
        counter = 2
        while unique_key in seen_keys:
            unique_key = f"{entry['key']}_{counter}"
            counter += 1
        if unique_key != entry["key"]:
            entry["key"] = unique_key
            entry["key_candidate"] = unique_key
        seen_keys.add(entry["key"])

        translations = build_pending_translations(entry.get("translations"), source_locale, target_locales, source_text)
        entry["translations"] = translations

        audit = entry.get("audit")
        if not isinstance(audit, dict):
            audit = {}
        audit.setdefault("ai_review", "pending")
        owner = audit.get("owner") or entry.get("owner")
        if owner:
            audit["owner"] = owner
        audit["human_review_required"] = bool(
            audit.get("human_review_required")
            if audit.get("human_review_required") is not None
            else infer_human_review_required(entry)
        )
        entry["audit"] = audit

        entry.setdefault("message_format", "plain")
        entry.setdefault("placeholders", [])
        entries.append(entry)

    manifest = {
        "manifest_version": "1.1",
        "source_locale": source_locale,
        "key_mode": key_mode,
        "task_mode": args.task_mode,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_locales": target_locales,
        "required_locale_coverage": required_locale_coverage,
        "target_outputs": target_outputs,
        "included_surfaces": included_surfaces,
        "max_entries_per_slice": max(1, args.max_entries_per_slice),
        "revision_loop_limit": max(1, args.revision_loop_limit),
        "entries": entries,
    }
    return manifest


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest stub to {output_path}")
    print(json.dumps({"entries": len(manifest["entries"]), "key_mode": manifest["key_mode"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
