#!/usr/bin/env python3
"""Flatten the model eval pack into a CSV for external eval tooling."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the i18n model eval pack to CSV.")
    parser.add_argument("pack", help="Path to assets/model-eval-pack.json.")
    parser.add_argument("--output", required=True, help="CSV output path.")
    return parser.parse_args()


def load_pack(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def case_value(case: dict[str, Any], path: list[str]) -> Any:
    current: Any = case
    for segment in path:
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def main() -> int:
    args = parse_args()
    pack_path = Path(args.pack).expanduser()
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pack = load_pack(pack_path)
    cases = pack.get("cases", [])
    if not isinstance(cases, list):
        print("Eval pack must contain a cases array.", file=sys.stderr)
        return 1

    fieldnames = [
        "case_id",
        "suite",
        "description",
        "tags",
        "old_entry_json",
        "candidate_entry_json",
        "existing_candidates_json",
        "expected_change_level",
        "expected_reuse_decision",
        "expected_review_decision",
        "expected_human_review_required",
        "expected_must_ask_for_context",
        "expected_reason_codes",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            if not isinstance(case, dict):
                continue
            writer.writerow(
                {
                    "case_id": case.get("case_id", ""),
                    "suite": case.get("suite", ""),
                    "description": case.get("description", ""),
                    "tags": "|".join(str(tag) for tag in case.get("tags", []) if str(tag).strip()),
                    "old_entry_json": compact_json(case_value(case, ["input", "old_entry"])),
                    "candidate_entry_json": compact_json(case_value(case, ["input", "candidate_entry"])),
                    "existing_candidates_json": compact_json(case_value(case, ["input", "existing_candidates"])),
                    "expected_change_level": case_value(case, ["expected", "change_level"]) or "",
                    "expected_reuse_decision": case_value(case, ["expected", "reuse_decision"]) or "",
                    "expected_review_decision": case_value(case, ["expected", "review_decision"]) or "",
                    "expected_human_review_required": case_value(case, ["expected", "human_review_required"]),
                    "expected_must_ask_for_context": case_value(case, ["expected", "must_ask_for_context"]),
                    "expected_reason_codes": "|".join(
                        str(code)
                        for code in (case_value(case, ["expected", "reason_codes"]) or [])
                        if str(code).strip()
                    ),
                }
            )

    print(f"Wrote eval CSV to {output_path}")
    print(json.dumps({"case_count": len(cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
