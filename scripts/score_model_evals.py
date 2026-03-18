#!/usr/bin/env python3
"""Score structured model predictions against the curated i18n eval pack."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCALAR_FIELDS = (
    "change_level",
    "reuse_decision",
    "review_decision",
    "human_review_required",
    "must_ask_for_context",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score model predictions against the i18n eval pack.")
    parser.add_argument("pack", help="Path to assets/model-eval-pack.json.")
    parser.add_argument("predictions", nargs="?", help="Path to a predictions JSON file.")
    parser.add_argument("--report", help="Optional JSON report output path.")
    parser.add_argument(
        "--emit-template",
        help="Optional output path for a blank predictions template derived from the eval pack.",
    )
    parser.add_argument(
        "--fail-on-thresholds",
        action="store_true",
        help="Exit non-zero when one or more success criteria are not met.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_scalar(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field == "change_level":
        return str(value).strip().upper()
    if field in {"reuse_decision", "review_decision"}:
        normalized = str(value).strip().lower().replace("_", "-").replace(" ", "-")
        aliases = {"newkey": "new-key", "humangate": "human-gate"}
        return aliases.get(normalized, normalized)
    if field in {"human_review_required", "must_ask_for_context"}:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "yes", "y", "1"}:
            return True
        if text in {"false", "no", "n", "0"}:
            return False
    return value


def normalize_reason_codes(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = value.split("|")
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = [value]
    normalized = []
    for item in candidates:
        code = str(item).strip().lower().replace("_", "-").replace(" ", "-")
        if code:
            normalized.append(code)
    return sorted(set(normalized))


def pack_cases(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = pack.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("Eval pack must contain a cases array.")
    indexed: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "").strip()
        if not case_id:
            continue
        indexed[case_id] = case
    return indexed


def normalize_prediction_entry(raw: dict[str, Any]) -> dict[str, Any]:
    actual = raw.get("actual") if isinstance(raw.get("actual"), dict) else raw
    normalized: dict[str, Any] = {"case_id": raw.get("case_id") or actual.get("case_id")}
    for field in SCALAR_FIELDS:
        normalized[field] = normalize_scalar(field, actual.get(field))
    normalized["reason_codes"] = normalize_reason_codes(actual.get("reason_codes"))
    return normalized


def prediction_case_id(raw: dict[str, Any]) -> str:
    if not isinstance(raw, dict):
        return ""
    if str(raw.get("case_id") or "").strip():
        return str(raw.get("case_id")).strip()
    actual = raw.get("actual")
    if isinstance(actual, dict) and str(actual.get("case_id") or "").strip():
        return str(actual.get("case_id")).strip()
    return ""


def build_template(case_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    template = []
    for case_id in sorted(case_index):
        template.append(
            {
                "case_id": case_id,
                "change_level": None,
                "reuse_decision": None,
                "review_decision": None,
                "human_review_required": None,
                "must_ask_for_context": None,
                "reason_codes": [],
            }
        )
    return template


def metric_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def main() -> int:
    args = parse_args()
    pack_path = Path(args.pack).expanduser()
    pack = load_json(pack_path)
    case_index = pack_cases(pack)

    if args.emit_template:
        dump_json(Path(args.emit_template).expanduser(), build_template(case_index))
        print(f"Wrote prediction template to {Path(args.emit_template).expanduser()}")
        if not args.predictions:
            return 0

    if not args.predictions:
        print("Predictions path is required unless --emit-template is used alone.", file=sys.stderr)
        return 1

    predictions_payload = load_json(Path(args.predictions).expanduser())
    raw_predictions = predictions_payload.get("predictions") if isinstance(predictions_payload, dict) else predictions_payload
    if not isinstance(raw_predictions, list):
        print("Predictions file must be a JSON array or an object with a predictions array.", file=sys.stderr)
        return 1

    predictions = {
        prediction_case_id(item): normalize_prediction_entry(item)
        for item in raw_predictions
        if prediction_case_id(item)
    }

    issues: list[dict[str, Any]] = []
    field_totals: Counter[str] = Counter()
    field_correct: Counter[str] = Counter()
    suite_totals: Counter[str] = Counter()
    suite_correct: Counter[str] = Counter()
    tag_totals: Counter[str] = Counter()
    tag_correct: Counter[str] = Counter()
    human_gate_gold = 0
    human_gate_hits = 0
    pass_predicted = 0
    pass_true_positive = 0
    reuse_predicted = 0
    reuse_true_positive = 0
    l2_l3_gold = 0
    l2_l3_hits = 0
    high_risk_l3_false_negatives = 0
    reason_required_total = 0
    reason_required_hits = 0

    for case_id, case in sorted(case_index.items()):
        suite = str(case.get("suite") or "unknown")
        tags = [str(tag) for tag in case.get("tags", []) if str(tag).strip()]
        expected = case.get("expected", {})
        if not isinstance(expected, dict):
            continue

        suite_totals[suite] += 1
        for tag in tags:
            tag_totals[tag] += 1

        actual = predictions.get(case_id)
        if actual is None:
            issues.append({"case_id": case_id, "severity": "error", "message": "missing prediction"})
            continue

        case_ok = True
        for field in SCALAR_FIELDS:
            if field not in expected:
                continue
            field_totals[field] += 1
            gold = normalize_scalar(field, expected.get(field))
            pred = actual.get(field)
            if pred == gold:
                field_correct[field] += 1
            else:
                case_ok = False
                issues.append(
                    {
                        "case_id": case_id,
                        "severity": "error",
                        "field": field,
                        "expected": gold,
                        "actual": pred,
                    }
                )

        gold_reasons = normalize_reason_codes(expected.get("reason_codes"))
        actual_reasons = normalize_reason_codes(actual.get("reason_codes"))
        if gold_reasons:
            reason_required_total += len(gold_reasons)
            reason_required_hits += sum(1 for code in gold_reasons if code in actual_reasons)
            missing_reasons = [code for code in gold_reasons if code not in actual_reasons]
            if missing_reasons:
                case_ok = False
                issues.append(
                    {
                        "case_id": case_id,
                        "severity": "warning",
                        "field": "reason_codes",
                        "expected_subset": gold_reasons,
                        "actual": actual_reasons,
                        "missing": missing_reasons,
                    }
                )

        if case_ok:
            suite_correct[suite] += 1
            for tag in tags:
                tag_correct[tag] += 1

        gold_change = normalize_scalar("change_level", expected.get("change_level"))
        pred_change = actual.get("change_level")
        if gold_change in {"L2", "L3"}:
            l2_l3_gold += 1
            if pred_change == gold_change:
                l2_l3_hits += 1

        candidate_entry = case.get("input", {}).get("candidate_entry", {})
        risk_level = str(candidate_entry.get("risk_level") or "").lower() if isinstance(candidate_entry, dict) else ""
        if gold_change == "L3" and risk_level == "high" and pred_change != "L3":
            high_risk_l3_false_negatives += 1

        gold_reuse = normalize_scalar("reuse_decision", expected.get("reuse_decision"))
        pred_reuse = actual.get("reuse_decision")
        if pred_reuse == "reuse":
            reuse_predicted += 1
            if gold_reuse == "reuse":
                reuse_true_positive += 1

        gold_review = normalize_scalar("review_decision", expected.get("review_decision"))
        pred_review = actual.get("review_decision")
        if gold_review == "human-gate":
            human_gate_gold += 1
            if pred_review == "human-gate":
                human_gate_hits += 1
        if pred_review == "pass":
            pass_predicted += 1
            if gold_review == "pass":
                pass_true_positive += 1

    metrics = {
        "field_accuracy": {
          field: metric_ratio(field_correct[field], field_totals[field])
          for field in SCALAR_FIELDS
          if field_totals[field] > 0
        },
        "reason_code_recall": metric_ratio(reason_required_hits, reason_required_total),
        "change_level_accuracy": metric_ratio(field_correct["change_level"], field_totals["change_level"]),
        "l2_l3_recall": metric_ratio(l2_l3_hits, l2_l3_gold),
        "high_risk_l3_false_negatives": high_risk_l3_false_negatives,
        "reuse_auto_precision": metric_ratio(reuse_true_positive, reuse_predicted),
        "review_human_gate_recall": metric_ratio(human_gate_hits, human_gate_gold),
        "review_pass_precision": metric_ratio(pass_true_positive, pass_predicted),
    }

    suite_breakdown = {
        suite: {
            "case_count": suite_totals[suite],
            "fully_correct_cases": suite_correct[suite],
            "case_accuracy": metric_ratio(suite_correct[suite], suite_totals[suite]),
        }
        for suite in sorted(suite_totals)
    }
    tag_breakdown = {
        tag: {
            "case_count": tag_totals[tag],
            "fully_correct_cases": tag_correct[tag],
            "case_accuracy": metric_ratio(tag_correct[tag], tag_totals[tag]),
        }
        for tag in sorted(tag_totals)
    }

    thresholds = pack.get("success_criteria", {})
    failures: list[dict[str, Any]] = []

    def check_threshold(metric_name: str, comparator: str, threshold_key: str) -> None:
        threshold = thresholds.get(threshold_key)
        metric = metrics.get(metric_name)
        if threshold is None or metric is None:
            return
        passed = metric >= threshold if comparator == ">=" else metric <= threshold
        if not passed:
            failures.append(
                {
                    "metric": metric_name,
                    "actual": metric,
                    "target": threshold,
                    "comparator": comparator,
                }
            )

    check_threshold("change_level_accuracy", ">=", "change_level_accuracy_min")
    check_threshold("l2_l3_recall", ">=", "l2_l3_recall_min")
    check_threshold("reuse_auto_precision", ">=", "reuse_auto_precision_min")
    check_threshold("review_human_gate_recall", ">=", "review_human_gate_recall_min")
    check_threshold("review_pass_precision", ">=", "review_pass_precision_min")
    check_threshold("high_risk_l3_false_negatives", "<=", "high_risk_l3_false_negative_max")

    report = {
        "pack": str(pack_path),
        "case_count": len(case_index),
        "prediction_count": len(predictions),
        "metrics": metrics,
        "suite_breakdown": suite_breakdown,
        "tag_breakdown": tag_breakdown,
        "threshold_failures": failures,
        "issues": issues,
    }

    if args.report:
        dump_json(Path(args.report).expanduser(), report)

    print(
        json.dumps(
            {
                "case_count": report["case_count"],
                "prediction_count": report["prediction_count"],
                "threshold_failures": len(failures),
                "issue_count": len(issues),
            },
            ensure_ascii=False,
        )
    )

    if args.fail_on_thresholds and failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
