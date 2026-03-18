#!/usr/bin/env python3
"""Emit delivery bundles from a canonical i18n manifest."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ANDROID_DIR_MAP = {
    "en": "values",
    "zh-Hans": "values-zh-rCN",
    "zh-Hant": "values-zh-rTW",
    "de": "values-de",
    "fr": "values-fr",
    "it": "values-it",
    "pt-BR": "values-pt-rBR",
    "es": "values-es",
    "ru": "values-ru",
    "ko": "values-ko",
    "hi": "values-hi",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate delivery bundles from a canonical manifest.")
    parser.add_argument("manifest", help="Path to the canonical manifest JSON.")
    parser.add_argument("--out-dir", required=True, help="Directory for generated artifacts.")
    parser.add_argument(
        "--formats",
        help="Optional comma-separated formats: manifest,csv,json,ios,android. Default: manifest target_outputs or all supported formats.",
    )
    parser.add_argument(
        "--locales",
        help="Optional comma-separated locale allowlist. Default: manifest required_locale_coverage, then target_locales, then all locales found in the manifest.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = value.split(",")
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]


def translation_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("value")
        return text if isinstance(text, str) else ""
    return ""


def placeholder_specs(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw = entry.get("placeholders")
    if isinstance(raw, list):
        specs: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                spec = dict(item)
                spec.setdefault("canonical", f"{{{name}}}")
                spec.setdefault("web", spec["canonical"])
                specs.append(spec)
            else:
                name = str(item).strip()
                if name:
                    specs.append({"name": name, "canonical": f"{{{name}}}", "web": f"{{{name}}}"})
        return specs
    return []


def adapt_platform_text(
    text: str,
    entry: dict[str, Any],
    platform: str,
    warnings: list[dict[str, Any]],
    locale: str,
) -> str:
    rendered = text
    for spec in placeholder_specs(entry):
        canonical = str(spec.get("canonical") or "")
        if not canonical:
            continue
        replacement = spec.get(platform)
        if replacement in (None, ""):
            if platform in {"ios", "android"}:
                warnings.append(
                    {
                        "key": str(entry.get("key") or ""),
                        "locale": locale,
                        "platform": platform,
                        "message": f"missing {platform} placeholder mapping for {spec.get('name')}; kept canonical token",
                    }
                )
            replacement = canonical
        rendered = rendered.replace(canonical, str(replacement))
    return rendered


def locales_from_manifest(manifest: dict[str, Any]) -> list[str]:
    locales: set[str] = set()
    for entry in manifest.get("entries", []):
        translations = entry.get("translations", {})
        if isinstance(translations, dict):
            locales.update(str(locale) for locale in translations.keys())
    return sorted(locales)


def safe_android_dir(locale: str) -> str:
    if locale in ANDROID_DIR_MAP:
        return ANDROID_DIR_MAP[locale]
    if "-" not in locale:
        return f"values-{locale}"
    parts = locale.split("-", 1)
    return f"values-{parts[0]}-r{parts[1].upper()}"


def safe_ios_dir(locale: str) -> str:
    return f"{locale}.lproj"


def write_manifest_copy(manifest: dict[str, Any], out_dir: Path) -> None:
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(manifest: dict[str, Any], locales: list[str], out_dir: Path) -> None:
    csv_path = out_dir / "localization-table.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "key",
                "locale",
                "value",
                "source_text",
                "screen",
                "component",
                "intent",
                "risk_level",
                "status",
            ]
        )
        for entry in manifest.get("entries", []):
            translations = entry.get("translations", {})
            for locale in locales:
                value = translation_value(translations.get(locale))
                if not value:
                    continue
                raw = translations.get(locale)
                status = raw.get("status") if isinstance(raw, dict) else ""
                writer.writerow(
                    [
                        entry.get("key", ""),
                        locale,
                        value,
                        entry.get("source_text", ""),
                        entry.get("screen", ""),
                        entry.get("component", ""),
                        entry.get("intent", ""),
                        entry.get("risk_level", ""),
                        status,
                    ]
                )


def write_json(manifest: dict[str, Any], locales: list[str], out_dir: Path) -> None:
    base = out_dir / "json"
    base.mkdir(parents=True, exist_ok=True)
    for locale in locales:
        payload = {}
        for entry in manifest.get("entries", []):
            translations = entry.get("translations", {})
            text = translation_value(translations.get(locale))
            if text:
                payload[str(entry.get("key"))] = text
        (base / f"{locale}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def escape_ios(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def write_ios(
    manifest: dict[str, Any],
    locales: list[str],
    out_dir: Path,
    warnings: list[dict[str, Any]],
) -> None:
    base = out_dir / "ios"
    base.mkdir(parents=True, exist_ok=True)
    for locale in locales:
        lines = []
        for entry in manifest.get("entries", []):
            translations = entry.get("translations", {})
            text = translation_value(translations.get(locale))
            if text:
                rendered = adapt_platform_text(text, entry, "ios", warnings, locale)
                lines.append(f'"{entry.get("key")}" = "{escape_ios(rendered)}";')
        target_dir = base / safe_ios_dir(locale)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "Localizable.strings").write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )


def write_android(
    manifest: dict[str, Any],
    locales: list[str],
    out_dir: Path,
    warnings: list[dict[str, Any]],
) -> None:
    base = out_dir / "android"
    base.mkdir(parents=True, exist_ok=True)
    for locale in locales:
        lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
        for entry in manifest.get("entries", []):
            translations = entry.get("translations", {})
            text = translation_value(translations.get(locale))
            if text:
                rendered = adapt_platform_text(text, entry, "android", warnings, locale)
                lines.append(f'    <string name="{entry.get("key")}">{escape(rendered)}</string>')
        lines.append("</resources>")
        target_dir = base / safe_android_dir(locale)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "strings.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    manifest: dict[str, Any],
    locales: list[str],
    out_dir: Path,
    formats: set[str],
    warnings: list[dict[str, Any]],
) -> None:
    summary = {
        "entry_count": len(manifest.get("entries", [])),
        "locales": locales,
        "formats": sorted(formats),
        "warnings": warnings,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    locales = (
        parse_list(args.locales)
        if args.locales
        else parse_list(manifest.get("required_locale_coverage"))
        or parse_list(manifest.get("target_locales"))
        or locales_from_manifest(manifest)
    )
    formats = set(
        parse_list(args.formats)
        if args.formats
        else parse_list(manifest.get("target_outputs")) or ["manifest", "csv", "json", "ios", "android"]
    )
    warnings: list[dict[str, Any]] = []

    if "manifest" in formats:
        write_manifest_copy(manifest, out_dir)
    if "csv" in formats:
        write_csv(manifest, locales, out_dir)
    if "json" in formats:
        write_json(manifest, locales, out_dir)
    if "ios" in formats:
        write_ios(manifest, locales, out_dir, warnings)
    if "android" in formats:
        write_android(manifest, locales, out_dir, warnings)
    write_summary(manifest, locales, out_dir, formats, warnings)

    print(f"Wrote delivery bundle to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
