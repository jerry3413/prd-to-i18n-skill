# Input Contract

## Supported Source Packages

Use one of these input profiles:

1. `folder-drop`
   Put exported resources in one folder and let the normalizer auto-detect them with `--input-dir`.
   This is the easiest path for non-technical users.
2. `raw-artifact-bundle`
   Provide a folder containing raw PRD materials such as Markdown, HTML, MHTML, Word, text-based PDF, XLSX, CSV, JSON, screenshots, or Figma exports.
   Use this when the team does not already have a copy list.
3. `platform-only`
   Provide exported iOS `.strings`, Android `strings.xml`, Web/App JSON, or CSV catalogs.
   This is the minimum viable mode and usually only gives `key + source_text`.
4. `platform-plus-sidecar`
   Provide platform exports plus a context sidecar keyed by `key`.
   This is the recommended non-API profile.
5. `catalog-snapshot`
   Provide a CSV or JSON export that already includes source text, existing translations, and metadata.
6. `api-adapter`
   Fetch the same information from an API and map it into the canonical snapshot format before reasoning.
7. `multimodal-evidence`
   Provide a PDF, screenshot set, or Figma export when the source text is not yet available as structured text.
   Pair it with at least a minimal context packet whenever possible.

## Beginner Path

When the user wants the simplest setup, prefer:

1. put iOS `.strings`, Android `strings.xml`, JSON locale files, or CSV catalogs into one folder
2. optionally provide one context sidecar such as `context.csv`
3. run:

   `python3 scripts/normalize_snapshot.py --input-dir ./exports --metadata ./context.csv --output /tmp/i18n-snapshot.json`

4. then build the manifest skeleton:

   `python3 scripts/build_manifest_stub.py /tmp/i18n-snapshot.json --task-mode change-sync --target-locales en,zh-Hans,de --target-outputs manifest,json,ios,android --output /tmp/i18n-manifest.json`

The folder path should be the default recommendation before asking the user to build explicit `--resource kind=...,path=...` descriptors.

If the user starts from raw PRD materials instead of exported catalogs, prefer:

1. put Markdown, HTML, MHTML, Word, PDF, XLSX, CSV, JSON, and screenshots into one folder
2. run:

   `python3 scripts/ingest_artifacts.py ./prd-bundle --output /tmp/evidence.json`

3. then extract conservative copy candidates:

   `python3 scripts/extract_copy_candidates.py /tmp/evidence.json --output /tmp/copy-candidates.json`

4. then build the manifest skeleton:

   `python3 scripts/build_manifest_stub.py /tmp/copy-candidates.json --task-mode new-build --target-locales en,zh-Hans,de --target-outputs manifest,json,ios,android --output /tmp/i18n-manifest.json`

For work that starts from raw materials, ask one thing early:

1. whether the user wants the whole document translated, a simple list of the copy that needs translation, or a final delivery package

Treat `draft-only` and `release-ready` as internal labels only. In user-facing conversation, ask in plain language instead of exposing those labels directly.

If the user confirms whole-document translation, ask for:

1. the target language
2. the preferred output form only if the user cares about the final shape; otherwise default to a complete translated version that follows the source structure

Do not ask localization-only delivery questions in that branch.

If the user confirms the final delivery path, then ask:

1. the target languages
2. whether this area was localized before, and if so ask for the old files or exports
3. what kind of deliverable the user wants, such as a source-copy list, translation table, reviewer handoff, or import-ready package
4. the final output format or handoff standard so the skill knows what the final delivery package must look like
5. a sample or template only when the result must match an existing internal system format

For draft copy-list work, if the result set is small and the user did not ask for a file, show the draft inline first. Only create a file by default when the result is large enough to be awkward in chat or when the next step depends on a saved artifact.

## Required Inputs By Task

Do not treat PRD as globally mandatory. Match the requirement to the task:

- `new-build`
  Require a PRD, a structured copy list, or another reliable source of new text.
  If the request is a final delivery request rather than a simple draft, require target languages, delivery content type, and target output formats or handoff standard. Older localization files are strongly recommended but not mandatory.
- `change-sync`
  Require changed source text such as a PRD diff, copy list, or updated source file, plus the current localization snapshot.
- `dedupe`
  Require the current localization snapshot. PRD is optional.
- `translation-fix`
  Require `key + source_text`, or a screenshot with minimal context. PRD is optional.
- `export-only`
  Require a ready manifest or localization snapshot plus target output formats. PRD is not required.

Recommended across modes:

- screenshot set or Figma export when context is visual
- terminology glossary or brand rules for stable wording
- character budgets for strict UI surfaces

For raw artifact bundles:

- prefer `docx` over screenshots when both contain the same text
- prefer text-based PDFs over scanned PDFs
- prefer CSV/XLSX tables over long free-form paragraphs

If the user only has PDFs or screenshots, the skill may still start extraction and context building, but final trust level depends on image quality and risk level. See [Multimodal Inputs](multimodal-inputs.md).

## Minimum Snapshot Fields

At minimum, ask the team to export or provide:

- `key`
- `source_locale`
- `source_text`

With only these fields, the skill can do basic duplicate checks, key suggestions, and bundle generation.

Without older localization files, do not present dedupe or reuse as high-confidence. For final delivery requests, ask whether the team has old files first, but continue if they say they do not.

If the source comes from a screenshot or PDF instead of a snapshot, require at least:

- visible source text or a user transcription
- `screen`
- `component`
- `background`

## Recommended Snapshot Fields

Ask for these fields whenever possible:

- `translations` for existing locales
- `background` or `description`
- `source_evidence` or enough information to infer it
- `screen` or another stable location hint
- `updated_at`
- `status`
- `deprecated` or `is_active`

With these fields, the skill can do reuse suggestions, change sync, and stronger review.

## Ideal Snapshot Fields

Add these fields to unlock strict review mode:

- `message_format`
- `placeholders`
- `length_limit`
- `risk_level`
- `owner`
- `screenshot_ref`

## Recommended Sidecar Columns

Use a CSV or JSON sidecar with these columns when the export does not contain context:

- `key`
- `source_text`
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

If the team only has a legacy `module` field, accept it as a weak fallback only. Prefer `screen` or `page` for new integrations.

## Field Aliases

The normalizer should treat common aliases as the same logical field:

- `source_text`: `source`, `original_text`, `english`, `en`, `原文`
- `background`: `context`, `description`, `scene`, `背景说明`, `场景`
- `screen`: `page`, `route`, `页面`
- `legacy_module`: `模块`, `module`
- `component`: `ui_component`, `控件`
- `intent`: `purpose`, `文案意图`, `意图`
- `screenshot_ref`: `screenshot_ref`, `figma_ref`, `截图`, `示意图`
- `extraction_mode`: `extraction_mode`, `evidence_mode`, `来源方式`
- `evidence_confidence`: `evidence_confidence`, `confidence`, `证据置信度`
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
  Use when placeholders and length budgets exist.

If data is incomplete, continue with the highest safe mode and record the downgrade in the manifest.

In user-facing conversation, avoid asking the user to choose `basic`, `review`, or `strict`. Infer the mode from the inputs and explain only the practical effect, for example: “I can proceed, but duplicate detection confidence will be lower.”

## Draft-Only Versus Release-Ready

When the user provides a PRD, PDF, or other raw product bundle, do not assume they only want ad hoc translation.

Use this split:

- `draft-only`
  The user explicitly wants extraction, rough translation, or a draft table only.
- `release-ready`
  The user is preparing localization for handoff, import, delivery, or release.

These labels are for internal reasoning. When talking to users, ask in plain language whether they want a simple list of the copy that needs translation first or a final package the team can use directly.

For `release-ready`, collect:

- the current localization baseline
- target outputs or handoff standard

If either is missing, do not silently invent a final delivery format. Stop at a draft manifest or CSV only after explaining the downgrade.
If the downgraded draft result is small, prefer showing it inline first instead of silently creating a file.

## Ambiguous Context Rule

When `source_text` is short or generic, such as `Photos`, `Continue`, `Open`, or `Done`, treat context as mandatory. If the user cannot provide enough context, downgrade to `basic` mode and mark the entry for human review instead of auto-finalizing it.

## Canonical Placeholder Rule

For cross-platform delivery, prefer canonical named placeholders such as `{count}` inside the manifest. Let exporters adapt them to iOS, Android, or Web formats instead of storing a different master string for every platform.
