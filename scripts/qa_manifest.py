#!/usr/bin/env python3
"""Run deterministic checks on a canonical i18n manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PLACEHOLDER_RE = re.compile(
    r"%\d+\$[@dfs]|%[@dfs]|{{[^{}]+}}|{[^{}]+}|</?[\w:-]+(?:\s[^<>]*)?>"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate placeholder, length, and key integrity.")
    parser.add_argument("manifest", help="Path to the canonical manifest JSON.")
    parser.add_argument("--report", help="Optional JSON report output path.")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning"],
        default="error",
        help="Exit non-zero on errors only or on warnings too.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def translation_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("value")
        return text if isinstance(text, str) else ""
    return ""


def field(entry: dict[str, Any], name: str) -> Any:
    if name in entry:
        return entry[name]
    constraints = entry.get("constraints")
    if isinstance(constraints, dict) and name in constraints:
        return constraints[name]
    audit = entry.get("audit")
    if isinstance(audit, dict) and name in audit:
        return audit[name]
    return None


def extract_placeholders(text: str) -> list[str]:
    return PLACEHOLDER_RE.findall(text or "")


def placeholder_specs(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw = entry.get("placeholders")
    if isinstance(raw, list) and raw:
        specs: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                spec = dict(item)
                spec.setdefault("canonical", f"{{{name}}}")
                specs.append(spec)
            else:
                name = str(item).strip()
                if name:
                    specs.append({"name": name, "canonical": f"{{{name}}}"})
        return specs

    legacy = entry.get("variables")
    if isinstance(legacy, list):
        return [{"name": str(item), "canonical": f"{{{item}}}"} for item in legacy if str(item).strip()]
    return []


def parse_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]


def required_platforms(manifest: dict[str, Any]) -> list[str]:
    outputs = set(parse_string_list(manifest.get("target_outputs")))
    platforms = []
    if "ios" in outputs:
        platforms.append("ios")
    if "android" in outputs:
        platforms.append("android")
    if "json" in outputs:
        platforms.append("web")
    if outputs:
        return platforms
    return ["ios", "android", "web"]


def required_locales(manifest: dict[str, Any]) -> list[str]:
    locales = parse_string_list(manifest.get("required_locale_coverage"))
    if locales:
        return locales
    return parse_string_list(manifest.get("target_locales"))


def source_evidence(entry: dict[str, Any]) -> dict[str, Any]:
    payload = entry.get("source_evidence")
    return payload if isinstance(payload, dict) else {}


def max_chars(length_limit: Any) -> int | None:
    if isinstance(length_limit, int):
        return length_limit
    if isinstance(length_limit, dict):
        value = length_limit.get("max_chars")
        return value if isinstance(value, int) else None
    if isinstance(length_limit, str):
        match = re.search(r"(\d+)", length_limit)
        return int(match.group(1)) if match else None
    return None


def severity_rank(level: str) -> int:
    return 2 if level == "error" else 1


def add_issue(issues: list[dict[str, Any]], severity: str, key: str, message: str, locale: str | None = None) -> None:
    payload: dict[str, Any] = {"severity": severity, "key": key, "message": message}
    if locale:
        payload["locale"] = locale
    issues.append(payload)


def validate_entry(
    entry: dict[str, Any],
    manifest: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    key = str(entry.get("key") or "")
    source_text = str(entry.get("source_text") or "")
    specs = placeholder_specs(entry)
    evidence = source_evidence(entry)
    coverage_locales = required_locales(manifest)
    source_locale = str(manifest.get("source_locale") or "en")
    required_output_platforms = required_platforms(manifest)

    if not key:
        add_issue(issues, "error", "<missing>", "entry is missing key")
        return
    if not source_text:
        add_issue(issues, "error", key, "entry is missing source_text")

    source_placeholders = extract_placeholders(source_text)
    declared_tokens = [str(spec.get("canonical") or "") for spec in specs if str(spec.get("canonical") or "")]
    declared_names = [str(spec.get("name") or "") for spec in specs if str(spec.get("name") or "")]

    if specs:
        if len(declared_names) != len(set(declared_names)):
            add_issue(issues, "error", key, "placeholder names must be unique")
        missing_from_source = [token for token in declared_tokens if token not in source_placeholders]
        if missing_from_source:
            add_issue(
                issues,
                "error",
                key,
                f"declared placeholders are not present in source_text: {', '.join(missing_from_source)}",
            )
        for spec in specs:
            for platform in required_output_platforms:
                if spec.get(platform) in (None, ""):
                    add_issue(
                        issues,
                        "warning",
                        key,
                        f"placeholder {spec.get('name')} is missing {platform} mapping",
                    )
        if entry.get("message_format") == "named-template":
            named_in_source = [token for token in source_placeholders if token.startswith("{") and token.endswith("}")]
            undeclared = [token for token in named_in_source if token not in declared_tokens]
            if undeclared:
                add_issue(
                    issues,
                    "warning",
                    key,
                    f"source_text contains undeclared named placeholders: {', '.join(undeclared)}",
                )

    translations = entry.get("translations", {})
    if not isinstance(translations, dict):
        add_issue(issues, "error", key, "translations must be an object keyed by locale")
        return

    for locale in coverage_locales:
        raw_value = translations.get(locale)
        text = translation_value(raw_value)
        if locale == source_locale:
            if not text:
                add_issue(issues, "error", key, f"missing required source locale translation for {locale}", locale=locale)
            continue
        if not text:
            add_issue(issues, "error", key, f"missing required locale translation for {locale}", locale=locale)

    for locale, raw_value in translations.items():
        text = translation_value(raw_value)
        if not text:
            continue
        translated_placeholders = extract_placeholders(text)
        if Counter(source_placeholders) != Counter(translated_placeholders):
            add_issue(
                issues,
                "error",
                key,
                "placeholder set differs from source_text",
                locale=locale,
            )
        elif source_placeholders != translated_placeholders:
            add_issue(
                issues,
                "warning",
                key,
                "placeholder order differs from source_text",
                locale=locale,
            )

        limit = max_chars(field(entry, "length_limit"))
        if limit is not None and len(text) > limit:
            add_issue(
                issues,
                "warning",
                key,
                f"translation length {len(text)} exceeds max_chars {limit}",
                locale=locale,
            )

    risk_level = str(field(entry, "risk_level") or "").lower()
    if risk_level == "high" and not field(entry, "human_review_required"):
        add_issue(issues, "warning", key, "high-risk entry should require human review")
    if risk_level == "high" and not field(entry, "owner"):
        add_issue(issues, "warning", key, "high-risk entry is missing an owner")
    if not evidence:
        add_issue(issues, "warning", key, "source_evidence is missing")
    else:
        confidence = str(evidence.get("confidence") or "").lower()
        extraction_mode = str(evidence.get("extraction_mode") or "").lower()
        if confidence == "low" and risk_level in {"medium", "high"} and not field(entry, "human_review_required"):
            add_issue(
                issues,
                "error",
                key,
                "low-confidence source evidence for medium/high-risk copy must require human review",
            )
        if extraction_mode in {"vision", "ocr"} and risk_level == "high" and not field(entry, "human_review_required"):
            add_issue(
                issues,
                "error",
                key,
                "high-risk vision/OCR-derived copy cannot auto-complete without human review",
            )

    if not field(entry, "intent") or not field(entry, "background"):
        add_issue(issues, "warning", key, "context is incomplete for review")


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser()
    manifest = load_manifest(manifest_path)
    entries = manifest.get("entries", [])
    issues: list[dict[str, Any]] = []

    if not isinstance(entries, list):
        print("Manifest must contain an entries array", file=sys.stderr)
        return 1

    seen_keys: Counter[str] = Counter()
    included_surfaces = set(parse_string_list(manifest.get("included_surfaces")))
    for entry in entries:
        if isinstance(entry, dict):
            key = str(entry.get("key") or "")
            if key:
                seen_keys[key] += 1

    for key, count in seen_keys.items():
        if count > 1:
            add_issue(issues, "error", key, f"duplicate key appears {count} times")

    for entry in entries:
        if isinstance(entry, dict):
            if included_surfaces:
                entry_surface = str(entry.get("surface") or "").strip()
                if entry_surface and entry_surface not in included_surfaces:
                    add_issue(
                        issues,
                        "error",
                        str(entry.get("key") or "<missing>"),
                        f"entry surface {entry_surface} is outside included_surfaces",
                    )
            validate_entry(entry, manifest, issues)
        else:
            add_issue(issues, "error", "<unknown>", "entry is not an object")

    report = {
        "manifest": str(manifest_path),
        "entry_count": len(entries),
        "issues": issues,
        "summary": {
            "errors": sum(1 for issue in issues if issue["severity"] == "error"),
            "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
        },
    }

    if args.report:
        Path(args.report).expanduser().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report["summary"], ensure_ascii=False))

    if args.fail_on == "warning" and issues:
        return 1
    if args.fail_on == "error" and any(issue["severity"] == "error" for issue in issues):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
