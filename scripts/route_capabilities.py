#!/usr/bin/env python3
"""Recommend the safest extraction path for multimodal localization inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route localization evidence through the right capability path.")
    parser.add_argument(
        "--input-kind",
        required=True,
        choices=[
            "markdown",
            "snapshot",
            "text-pdf",
            "scanned-pdf",
            "screenshot",
            "figma-export",
            "mixed",
        ],
        help="Primary evidence type.",
    )
    parser.add_argument("--native-vision", action="store_true", help="Runtime can inspect images/PDFs directly.")
    parser.add_argument("--vision-extension", action="store_true", help="External vision/OCR integration is configured.")
    parser.add_argument("--local-ocr", action="store_true", help="Local OCR or PDF extraction tooling is available.")
    parser.add_argument(
        "--risk-level",
        default="low",
        choices=["low", "medium", "high"],
        help="Highest risk level in the current slice.",
    )
    parser.add_argument(
        "--has-structured-text",
        action="store_true",
        help="The package already includes reliable structured text, even if screenshots or PDFs are also attached.",
    )
    parser.add_argument(
        "--exact-text-required",
        action="store_true",
        help="Exact wording matters for this slice, such as legal, pricing, or identity flows.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. If omitted, prints to stdout.",
    )
    return parser.parse_args()


def build_route(args: argparse.Namespace) -> dict:
    input_kind = args.input_kind
    risk_level = args.risk_level
    exact = args.exact_text_required

    if input_kind in {"markdown", "snapshot"} or (input_kind == "mixed" and args.has_structured_text):
        route = {
            "recommended_path": "text-first",
            "confidence": "high" if input_kind != "mixed" else "medium",
            "why": (
                "Structured text is already available."
                if input_kind != "mixed"
                else "Structured text is available, so screenshots or PDFs should be treated as disambiguation evidence rather than the primary text source."
            ),
            "blocking_requirements": [],
            "suggested_questions": (
                ["Use screenshots only when a short label or layout-dependent string is still ambiguous."]
                if input_kind == "mixed"
                else []
            ),
            "next_step": "Proceed to normalization and manifest building.",
        }
        return route

    if input_kind == "text-pdf":
        route = {
            "recommended_path": "text-first",
            "confidence": "high" if not exact else "medium",
            "why": "The PDF is text-based and can be treated as structured text after extraction.",
            "blocking_requirements": [],
            "suggested_questions": [
                "Confirm that the PDF text is selectable if the reading order looks complex."
            ]
            if exact
            else [],
            "next_step": "Extract text, verify section boundaries, then continue as text-first.",
        }
        return route

    if exact and risk_level in {"medium", "high"}:
        blocking = [
            "Need exact verified text before auto-completing this slice.",
        ]
    else:
        blocking = []

    if args.native_vision:
        return {
            "recommended_path": "native-vision",
            "confidence": "medium",
            "why": "The runtime can inspect the non-text evidence directly.",
            "blocking_requirements": blocking,
            "suggested_questions": [
                "Provide screen, component, and background for ambiguous labels."
            ],
            "next_step": "Use native vision for extraction, then keep ambiguous or risky entries gated.",
        }

    if args.vision_extension:
        return {
            "recommended_path": "vision-extension",
            "confidence": "medium",
            "why": "A configured external vision/OCR service can extract text and visual cues.",
            "blocking_requirements": blocking,
            "suggested_questions": [
                "Confirm the extension is configured and trusted for this workspace."
            ],
            "next_step": "Use the extension for extraction, then continue through normal manifest review.",
        }

    if args.local_ocr:
        return {
            "recommended_path": "local-ocr",
            "confidence": "low" if risk_level == "high" else "medium",
            "why": "No direct vision path exists, but local OCR/tooling can provide draft text.",
            "blocking_requirements": blocking,
            "suggested_questions": [
                "Confirm exact wording manually for long, ambiguous, or high-risk strings."
            ],
            "next_step": "Run OCR or text extraction locally, then treat the result as draft evidence.",
        }

    return {
        "recommended_path": "manual-fallback",
        "confidence": "low",
        "why": "No structured text, native vision, extension, or local OCR is available.",
        "blocking_requirements": [
            "Need source_text, screen, component, and background from the user."
        ]
        + blocking,
        "suggested_questions": [
            "Provide the exact source text.",
            "Provide screen, component, and one-sentence background.",
        ],
        "next_step": "Continue only in basic mode until the user supplies the minimum context packet.",
    }


def main() -> int:
    args = parse_args()
    route = build_route(args)
    payload = json.dumps(route, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
        print(f"Wrote capability route to {output_path}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
