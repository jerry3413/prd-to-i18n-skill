#!/usr/bin/env python3
"""Run deterministic smoke checks for the i18n delivery pipeline skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
ASSETS_DIR = SKILL_ROOT / "assets"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(SKILL_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_minimal_docx(path: Path) -> None:
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Identity Camera</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Shown while the user is aligning a document in the camera frame.</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>页面</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>控件</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>文案</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>背景说明</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>identity_camera</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>title</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Obverse Example</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Reference image title shown above the example card.</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:sectPr/>
  </w:body>
</w:document>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("word/document.xml", document_xml)


def create_minimal_xlsx(path: Path) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""
    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Gallery" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
    sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>页面</t></is></c>
      <c r="B1" t="inlineStr"><is><t>控件</t></is></c>
      <c r="C1" t="inlineStr"><is><t>文案</t></is></c>
      <c r="D1" t="inlineStr"><is><t>背景说明</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>gallery</t></is></c>
      <c r="B2" t="inlineStr"><is><t>button</t></is></c>
      <c r="C2" t="inlineStr"><is><t>Open album</t></is></c>
      <c r="D2" t="inlineStr"><is><t>Secondary action that opens the system album picker.</t></is></c>
    </row>
  </sheetData>
</worksheet>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def build_parallel_safe_manifest() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "source_locale": "en",
        "key_mode": "canonical",
        "generated_at": "2026-03-17T10:00:00Z",
        "entries": [
            {
                "key": "app_gallery_button_open_camera",
                "screen": "gallery",
                "component": "primary_button",
                "intent": "open_camera",
                "source_text": "Open camera",
                "background": "Primary button that opens the in-app camera from the gallery.",
                "source_evidence": {
                    "extraction_mode": "snapshot-export",
                    "confidence": "high",
                    "verified_text": True,
                    "artifacts": [],
                },
                "change_level": "L1",
                "risk_level": "low",
                "message_format": "plain",
                "placeholders": [],
                "translations": {
                    "en": {"value": "Open camera", "status": "approved"},
                    "zh-Hans": {"value": "打开相机", "status": "ai-reviewed"},
                },
                "audit": {"human_review_required": False, "owner": "gallery-owner"},
            },
            {
                "key": "app_gallery_button_open_album",
                "screen": "gallery",
                "component": "secondary_button",
                "intent": "open_album",
                "source_text": "Open album",
                "background": "Secondary button that opens the system album picker from the gallery.",
                "source_evidence": {
                    "extraction_mode": "snapshot-export",
                    "confidence": "high",
                    "verified_text": True,
                    "artifacts": [],
                },
                "change_level": "L1",
                "risk_level": "low",
                "message_format": "plain",
                "placeholders": [],
                "translations": {
                    "en": {"value": "Open album", "status": "approved"},
                    "zh-Hans": {"value": "打开相册", "status": "ai-reviewed"},
                },
                "audit": {"human_review_required": False, "owner": "gallery-owner"},
            },
        ],
    }


def build_large_parallel_manifest(count: int) -> dict[str, Any]:
    entries = []
    for index in range(count):
        entries.append(
            {
                "key": f"app_gallery_button_open_item_{index}",
                "screen": "gallery",
                "component": "primary_button",
                "intent": f"open_item_{index}",
                "source_text": f"Open item {index}",
                "background": "Primary button that opens an item from the gallery list.",
                "source_evidence": {
                    "extraction_mode": "snapshot-export",
                    "confidence": "high",
                    "verified_text": True,
                    "artifacts": [],
                },
                "change_level": "L1",
                "risk_level": "low",
                "message_format": "plain",
                "placeholders": [],
                "translations": {
                    "en": {"value": f"Open item {index}", "status": "source"},
                    "zh-Hans": {"value": f"打开条目 {index}", "status": "draft"},
                },
                "audit": {"human_review_required": False, "owner": "gallery-owner"},
            }
        )
    return {
        "manifest_version": "1.1",
        "source_locale": "en",
        "key_mode": "canonical",
        "generated_at": "2026-03-18T00:00:00Z",
        "target_locales": ["en", "zh-Hans"],
        "required_locale_coverage": ["en", "zh-Hans"],
        "target_outputs": ["manifest", "json"],
        "max_entries_per_slice": 50,
        "revision_loop_limit": 2,
        "entries": entries,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="i18n-smoke-") as temp_dir:
        temp = Path(temp_dir)

        raw_bundle_dir = temp / "raw-prd-bundle"
        raw_bundle_dir.mkdir(parents=True, exist_ok=True)
        (raw_bundle_dir / "sample-prd.md").write_text(
            (ASSETS_DIR / "sample-prd.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        create_minimal_docx(raw_bundle_dir / "sample.docx")
        create_minimal_xlsx(raw_bundle_dir / "sample.xlsx")

        evidence_path = temp / "evidence.json"
        run_script(
            str(SCRIPTS_DIR / "ingest_artifacts.py"),
            str(raw_bundle_dir),
            "--output",
            str(evidence_path),
        )
        evidence = load_json(evidence_path)
        expect(evidence["summary"]["artifact_count"] == 3, "artifact ingestion should discover markdown, docx, and xlsx inputs")
        expect(evidence["summary"]["block_count"] >= 5, "artifact ingestion should extract structured text blocks from raw PRD artifacts")

        copy_candidates_path = temp / "copy-candidates.json"
        run_script(
            str(SCRIPTS_DIR / "extract_copy_candidates.py"),
            str(evidence_path),
            "--output",
            str(copy_candidates_path),
        )
        copy_candidates = load_json(copy_candidates_path)
        extracted_texts = {entry["source_text"] for entry in copy_candidates["entries"]}
        expect("Ad limit reached today" in extracted_texts, "markdown extraction should recover explicit toast copy")
        expect("Obverse Example" in extracted_texts, "docx extraction should recover table-based copy")
        expect("Open album" in extracted_texts, "xlsx extraction should recover worksheet row copy")
        expect(
            copy_candidates["suggested_target_locales"] == ["zh-Hans", "en", "de"],
            "copy extraction should preserve explicit target locale hints from the PRD",
        )

        mixed_route_path = temp / "route-mixed.json"
        run_script(
            str(SCRIPTS_DIR / "route_capabilities.py"),
            "--input-kind",
            "mixed",
            "--has-structured-text",
            "--risk-level",
            "medium",
            "--output",
            str(mixed_route_path),
        )
        mixed_route = load_json(mixed_route_path)
        expect(mixed_route["recommended_path"] == "text-first", "mixed input with structured text should route to text-first")

        vision_route_path = temp / "route-vision.json"
        run_script(
            str(SCRIPTS_DIR / "route_capabilities.py"),
            "--input-kind",
            "screenshot",
            "--vision-extension",
            "--risk-level",
            "medium",
            "--output",
            str(vision_route_path),
        )
        vision_route = load_json(vision_route_path)
        expect(vision_route["recommended_path"] == "vision-extension", "screenshot input should use configured vision extension")

        risky_plan_path = temp / "plan-risky.json"
        run_script(
            str(SCRIPTS_DIR / "plan_execution.py"),
            str(ASSETS_DIR / "sample-approved-manifest.json"),
            "--output",
            str(risky_plan_path),
        )
        risky_plan = load_json(risky_plan_path)
        expect(risky_plan["summary"]["serial_translation_entries"] == 2, "sample-approved manifest should stay fully serial")
        expect(risky_plan["summary"]["parallel_translation_groups"] == 0, "sample-approved manifest should not open parallel groups")

        safe_manifest_path = temp / "parallel-safe-manifest.json"
        safe_plan_path = temp / "plan-safe.json"
        write_json(safe_manifest_path, build_parallel_safe_manifest())
        run_script(
            str(SCRIPTS_DIR / "plan_execution.py"),
            str(safe_manifest_path),
            "--output",
            str(safe_plan_path),
        )
        safe_plan = load_json(safe_plan_path)
        expect(safe_plan["summary"]["serial_translation_entries"] == 0, "safe manifest should avoid serial translation entries")
        expect(safe_plan["summary"]["parallel_translation_groups"] == 1, "safe manifest should group low-risk entries in parallel")

        large_manifest_path = temp / "large-parallel-manifest.json"
        large_plan_path = temp / "plan-large.json"
        write_json(large_manifest_path, build_large_parallel_manifest(55))
        run_script(
            str(SCRIPTS_DIR / "plan_execution.py"),
            str(large_manifest_path),
            "--output",
            str(large_plan_path),
        )
        large_plan = load_json(large_plan_path)
        expect(large_plan["summary"]["parallel_translation_groups"] == 2, "large safe manifest should be split by max_entries_per_slice")

        normalize_dir = temp / "exports"
        normalize_dir.mkdir(parents=True, exist_ok=True)
        (normalize_dir / "sample-en-ios.strings").write_text(
            (ASSETS_DIR / "sample-en-ios.strings").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (normalize_dir / "sample-en-android.xml").write_text(
            (ASSETS_DIR / "sample-en-android.xml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        normalized_snapshot_path = temp / "normalized-snapshot.json"
        run_script(
            str(SCRIPTS_DIR / "normalize_snapshot.py"),
            "--input-dir",
            str(normalize_dir),
            "--metadata",
            str(ASSETS_DIR / "sample-context.csv"),
            "--output",
            str(normalized_snapshot_path),
        )
        normalized_snapshot = load_json(normalized_snapshot_path)
        expect(normalized_snapshot["entries"], "input-dir normalization should discover at least one entry")
        expect(
            normalized_snapshot["inputs"]["input_dirs"] == [str(normalize_dir)],
            "normalized snapshot should record the discovered input directory",
        )

        manifest_stub_path = temp / "manifest-stub.json"
        run_script(
            str(SCRIPTS_DIR / "build_manifest_stub.py"),
            str(copy_candidates_path),
            "--task-mode",
            "new-build",
            "--target-locales",
            "en,zh-Hans,de",
            "--target-outputs",
            "manifest,json,ios,android",
            "--output",
            str(manifest_stub_path),
        )
        manifest_stub = load_json(manifest_stub_path)
        expect(manifest_stub["entries"], "manifest stub should accept copy-candidates packages")
        expect(any(entry["source_text"] == "Ad limit reached today" for entry in manifest_stub["entries"]), "manifest stub should preserve extracted copy candidates")

        snapshot_manifest_stub_path = temp / "snapshot-manifest-stub.json"
        run_script(
            str(SCRIPTS_DIR / "build_manifest_stub.py"),
            str(normalized_snapshot_path),
            "--task-mode",
            "change-sync",
            "--target-locales",
            "en,zh-Hans,de",
            "--target-outputs",
            "manifest,json,ios,android",
            "--output",
            str(snapshot_manifest_stub_path),
        )
        snapshot_manifest_stub = load_json(snapshot_manifest_stub_path)
        expect(snapshot_manifest_stub["target_locales"] == ["en", "zh-Hans", "de"], "manifest stub should preserve requested target locales")
        expect(snapshot_manifest_stub["revision_loop_limit"] == 2, "manifest stub should set revision loop limit")
        expect(snapshot_manifest_stub["entries"], "manifest stub should contain entries")

        qa_report_path = temp / "qa-report.json"
        run_script(
            str(SCRIPTS_DIR / "qa_manifest.py"),
            str(ASSETS_DIR / "sample-approved-manifest.json"),
            "--report",
            str(qa_report_path),
        )
        qa_report = load_json(qa_report_path)
        expect(qa_report["summary"]["errors"] == 0, "sample-approved manifest should pass deterministic QA")

        bundle_dir = temp / "bundle"
        run_script(
            str(SCRIPTS_DIR / "emit_delivery_bundle.py"),
            str(ASSETS_DIR / "sample-placeholder-manifest.json"),
            "--out-dir",
            str(bundle_dir),
            "--formats",
            "manifest,json,ios,android",
        )
        ios_text = (bundle_dir / "ios" / "en.lproj" / "Localizable.strings").read_text(encoding="utf-8")
        android_text = (bundle_dir / "android" / "values" / "strings.xml").read_text(encoding="utf-8")
        summary = load_json(bundle_dir / "summary.json")
        expect("%1$ld" in ios_text, "iOS export should adapt named placeholders to iOS format")
        expect("%1$d" in android_text, "Android export should adapt named placeholders to Android format")
        expect(not summary["warnings"], "sample placeholder manifest should export without placeholder warnings")

        print(
            json.dumps(
                {
                    "checks": 13,
                    "status": "passed",
                    "temp_dir": str(temp),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
