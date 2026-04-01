# Input Contract

This file defines accepted input packages and field expectations. It does not define user-facing intake or fallback policy.

## Contents

- Supported Input Profiles
- Preferred Paths
- Required Inputs By Task
- Minimum Snapshot Fields
- Recommended Snapshot Fields
- Ideal Snapshot Fields
- Minimum Context For Visual Inputs
- Recommended Sidecar Columns
- Field Aliases
- Capability Modes

## Supported Input Profiles

Use one of these profiles:

1. `folder-drop`
   One folder containing exported resources for auto-discovery with `--input-dir`.
2. `raw-artifact-bundle`
   One folder containing raw PRD materials such as Markdown, HTML, MHTML, Word, PDF, XLSX, CSV, JSON, screenshots, or Figma exports.
3. `platform-only`
   iOS `.strings`, Android `strings.xml`, Web/App JSON, or CSV catalogs.
4. `platform-plus-sidecar`
   Platform exports plus one context sidecar keyed by `key`.
5. `catalog-snapshot`
   A CSV or JSON export that already includes source text, translations, and metadata.
6. `api-adapter`
   API output mapped into the canonical snapshot shape before reasoning.
7. `multimodal-evidence`
   Screenshot, PDF, or Figma evidence when structured text is not yet available.

## Preferred Paths

Prefer the simplest valid path first:

- exported resources -> `python3 scripts/normalize_snapshot.py --input-dir ./exports --metadata ./context.csv --output /tmp/i18n-snapshot.json`
- raw artifact bundle -> `python3 scripts/ingest_artifacts.py ./prd-bundle --output /tmp/evidence.json`
- extracted candidate path -> `python3 scripts/extract_copy_candidates.py /tmp/evidence.json --output /tmp/copy-candidates.json`
- manifest skeleton -> `python3 scripts/build_manifest_stub.py <source> --output /tmp/i18n-manifest.json`

Use explicit `--resource kind=...,path=...` descriptors only when auto-discovery is not enough.

## Required Inputs By Task

- `new-build`
  Require a PRD, a copy list, an evidence package, or another reliable source of new text.
- `change-sync`
  Require changed source text plus the current localization snapshot.
- `dedupe`
  Require the current localization snapshot.
- `translation-fix`
  Require `key + source_text`, or screenshot evidence plus minimal context.
- `export-only`
  Require a ready manifest or localization snapshot plus confirmed target outputs.

## Minimum Snapshot Fields

At minimum, provide:

- `key`
- `source_locale`
- `source_text`

With only these fields, the workflow can do basic duplicate checks, key suggestions, and bundle generation.

## Recommended Snapshot Fields

Provide these whenever possible:

- `translations`
- `background`
- `source_evidence`
- `screen`
- `component`
- `intent`
- `updated_at`
- `status`
- `deprecated` or `is_active`

## Ideal Snapshot Fields

Add these to unlock stricter review:

- `message_format`
- `placeholders`
- `length_limit`
- `risk_level`
- `owner`
- `screenshot_ref`

## Minimum Context For Visual Inputs

If the source starts from screenshots or PDF evidence instead of a snapshot, require at least:

- visible source text or user transcription
- `screen`
- `component`
- `background`

## Recommended Sidecar Columns

Use a CSV or JSON sidecar with these columns when the export does not contain enough context:

- `key`
- `source_text`
- `surface`
- `screen`
- `component`
- `intent`
- `background`
- `screenshot_ref`
- `extraction_mode`
- `evidence_confidence`
- `message_format`
- `placeholders`
- `length_limit`
- `risk_level`
- `owner`
- `status`
- `updated_at`

If the team only has a legacy `module` field, accept it as a weak fallback only.

## Field Aliases

Treat these aliases as the same logical field:

- `source_text`: `source`, `original_text`, `english`, `en`, `原文`
- `background`: `context`, `description`, `scene`, `背景说明`, `场景`
- `screen`: `page`, `route`, `页面`
- `legacy_module`: `模块`, `module`
- `component`: `ui_component`, `控件`
- `intent`: `purpose`, `文案意图`, `意图`
- `screenshot_ref`: `figma_ref`, `截图`, `示意图`
- `extraction_mode`: `evidence_mode`, `来源方式`
- `evidence_confidence`: `confidence`, `证据置信度`
- `length_limit`: `char_limit`, `长度限制`
- `placeholders`: `variables`, `占位符`
- `risk_level`: `risk`, `风险等级`
- `updated_at`: `last_updated`, `更新时间`

## Capability Modes

- `basic`
  Use when only `key + source_text` exist.
- `review`
  Use when context and existing translations exist.
- `strict`
  Use when placeholders, length limits, or platform mapping requirements exist.

If data is incomplete, continue with the highest safe mode and record the downgrade in the manifest.
