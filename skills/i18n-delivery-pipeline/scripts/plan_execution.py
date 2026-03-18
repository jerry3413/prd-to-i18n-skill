#!/usr/bin/env python3
"""Turn a canonical manifest into a serial/parallel execution plan."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PLACEHOLDER_RE = re.compile(r"%\d+\$[@dfs]|%[@dfs]|{{[^{}]+}}|{[^{}]+}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a serial/parallel execution plan from a manifest.")
    parser.add_argument("manifest", help="Path to the canonical manifest JSON.")
    parser.add_argument("--output", required=True, help="Path to the execution plan JSON.")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def int_setting(manifest: dict[str, Any], name: str, default: int) -> int:
    value = manifest.get(name)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def entry_field(entry: dict[str, Any], name: str) -> Any:
    if name in entry:
        return entry[name]
    audit = entry.get("audit")
    if isinstance(audit, dict) and name in audit:
        return audit[name]
    return None


def has_complete_context(entry: dict[str, Any]) -> bool:
    required = ("source_text", "screen", "component", "intent", "background")
    return all(entry.get(field) not in (None, "") for field in required)


def has_placeholders(entry: dict[str, Any]) -> bool:
    placeholders = entry.get("placeholders")
    if isinstance(placeholders, list) and placeholders:
        return True
    variables = entry.get("variables") or []
    if isinstance(variables, list) and variables:
        return True
    source_text = str(entry.get("source_text") or "")
    return bool(PLACEHOLDER_RE.search(source_text))


def strict_length(entry: dict[str, Any]) -> bool:
    length_limit = entry.get("length_limit")
    if isinstance(length_limit, dict):
        return str(length_limit.get("mode") or "").lower() == "strict"
    if isinstance(length_limit, str):
        return "strict" in length_limit.lower()
    if isinstance(length_limit, int):
        return True
    return False


def existing_match_status(entry: dict[str, Any]) -> str:
    existing = entry.get("existing_match")
    if isinstance(existing, dict):
        return str(existing.get("status") or "").lower()
    return ""


def human_checkpoint_required(entry: dict[str, Any]) -> bool:
    return bool(entry_field(entry, "human_review_required"))


def source_evidence(entry: dict[str, Any]) -> dict[str, Any]:
    evidence = entry.get("source_evidence")
    return evidence if isinstance(evidence, dict) else {}


def serial_reasons(entry: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    risk_level = str(entry.get("risk_level") or "").lower()
    change_level = str(entry.get("change_level") or "").upper()
    match_status = existing_match_status(entry)
    evidence = source_evidence(entry)
    extraction_mode = str(evidence.get("extraction_mode") or "").lower()
    confidence = str(evidence.get("confidence") or "").lower()
    verified_text = evidence.get("verified_text")

    if risk_level == "high":
        reasons.append("high-risk copy requires serial handling")
    if change_level in {"L2", "L3"}:
        reasons.append(f"{change_level} change needs fixed review gates")
    if confidence == "low":
        reasons.append("source evidence confidence is low")
    if extraction_mode in {"vision", "ocr"} and risk_level in {"medium", "high"}:
        reasons.append(f"{extraction_mode} evidence needs serial verification for risky copy")
    if verified_text is False:
        reasons.append("source text is not yet verified")
    if not has_complete_context(entry):
        reasons.append("context is incomplete")
    if has_placeholders(entry):
        reasons.append("placeholders require careful preservation")
    if strict_length(entry):
        reasons.append("strict length limit applies")
    if match_status in {"fuzzy", "conflict", "ambiguous"}:
        reasons.append(f"existing match status is {match_status}")
    if human_checkpoint_required(entry):
        reasons.append("human checkpoint required")
    return reasons


def is_parallel_safe(entry: dict[str, Any]) -> bool:
    risk_level = str(entry.get("risk_level") or "").lower()
    change_level = str(entry.get("change_level") or "").upper()
    if serial_reasons(entry):
        return False
    if risk_level not in {"low", "medium"}:
        return False
    if change_level not in {"", "L0", "L1"}:
        return False
    return True


def build_slice_key(entry: dict[str, Any]) -> str:
    screen = str(entry.get("screen") or "unknown-screen")
    risk = str(entry.get("risk_level") or "unknown-risk")
    return f"{screen}::{risk}"


def chunk_keys(keys: list[str], chunk_size: int) -> list[list[str]]:
    return [keys[index : index + chunk_size] for index in range(0, len(keys), chunk_size)]


def make_entry_summary(entry: dict[str, Any]) -> dict[str, Any]:
    evidence = source_evidence(entry)
    return {
        "key": entry.get("key"),
        "screen": entry.get("screen"),
        "risk_level": entry.get("risk_level"),
        "change_level": entry.get("change_level"),
        "extraction_mode": evidence.get("extraction_mode"),
        "evidence_confidence": evidence.get("confidence"),
        "parallel_safe": is_parallel_safe(entry),
        "serial_reasons": serial_reasons(entry),
    }


def build_plan(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("Manifest must contain an entries list")

    max_entries_per_slice = int_setting(manifest, "max_entries_per_slice", 50)
    revision_loop_limit = int_setting(manifest, "revision_loop_limit", 2)

    translation_parallel_groups: dict[str, list[str]] = defaultdict(list)
    review_parallel_groups: dict[str, list[str]] = defaultdict(list)
    serial_translation: list[dict[str, Any]] = []
    serial_review: list[dict[str, Any]] = []
    human_checkpoints: list[dict[str, Any]] = []
    entry_summaries: list[dict[str, Any]] = []

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        summary = make_entry_summary(raw_entry)
        entry_summaries.append(summary)

        key = str(raw_entry.get("key") or "")
        if not key:
            continue

        if is_parallel_safe(raw_entry):
            group = build_slice_key(raw_entry)
            translation_parallel_groups[group].append(key)
            review_parallel_groups[group].append(key)
        else:
            serial_translation.append(summary)
            serial_review.append(summary)

        if human_checkpoint_required(raw_entry) or str(raw_entry.get("risk_level") or "").lower() == "high":
            human_checkpoints.append(
                {
                    "key": key,
                    "owner": entry_field(raw_entry, "owner"),
                    "reason": serial_reasons(raw_entry) or ["manual gate required"],
                }
            )

    translation_groups = []
    review_groups = []
    for group, keys in sorted(translation_parallel_groups.items()):
        for index, chunk in enumerate(chunk_keys(keys, max_entries_per_slice), start=1):
            suffix = "" if len(keys) <= max_entries_per_slice else f"::part-{index}"
            translation_groups.append({"slice": f"{group}{suffix}", "keys": chunk})
    for group, keys in sorted(review_parallel_groups.items()):
        for index, chunk in enumerate(chunk_keys(keys, max_entries_per_slice), start=1):
            suffix = "" if len(keys) <= max_entries_per_slice else f"::part-{index}"
            review_groups.append({"slice": f"{group}{suffix}", "keys": chunk})

    plan = {
        "plan_version": "1.0",
        "manifest": str(manifest_path),
        "summary": {
            "entry_count": len(entry_summaries),
            "parallel_translation_groups": len(translation_groups),
            "parallel_review_groups": len(review_groups),
            "serial_translation_entries": len(serial_translation),
            "serial_review_entries": len(serial_review),
            "human_checkpoints": len(human_checkpoints),
            "max_entries_per_slice": max_entries_per_slice,
            "revision_loop_limit": revision_loop_limit,
        },
        "policy_notes": [
            "Freeze manifest structure before launching translators or reviewers.",
            "Use subagents for self-contained translation and review slices.",
            "Keep L2/L3, high-risk, placeholder-heavy, strict-length, or ambiguous entries serial.",
            "Route only independent low/medium-risk L0/L1 slices to parallel workers.",
            f"Split parallel slices larger than {max_entries_per_slice} entries.",
            f"After any failed review, loop the failed slice back through translator then reviewer no more than {revision_loop_limit} times before escalation.",
        ],
        "stages": [
            {
                "name": "freeze-manifest",
                "mode": "serial",
                "owner": "coordinator",
                "why": "Key decisions, change classification, and risk routing share context and must be stable before delegation.",
            },
            {
                "name": "translation",
                "mode": "mixed",
                "agent": "i18n-translator",
                "parallel_groups": translation_groups,
                "serial_entries": serial_translation,
            },
            {
                "name": "review",
                "mode": "mixed",
                "agent": "i18n-reviewer",
                "parallel_groups": review_groups,
                "serial_entries": serial_review,
            },
            {
                "name": "revision-loop",
                "mode": "serial",
                "owner": "coordinator",
                "why": f"Reviewer findings must be applied to the exact failed slice, then rechecked before continuing. Escalate after {revision_loop_limit} loops.",
            },
            {
                "name": "qa-and-export",
                "mode": "serial",
                "owner": "coordinator",
                "why": "Final QA and delivery bundle generation should run once on the merged manifest.",
            },
        ],
        "human_checkpoints": human_checkpoints,
        "entries": entry_summaries,
    }
    return plan


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser()
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    plan = build_plan(manifest, manifest_path)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote execution plan to {output_path}")
    print(json.dumps(plan["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
