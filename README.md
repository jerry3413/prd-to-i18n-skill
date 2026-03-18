# PRD to I18n Skill

Turn messy PRDs, screenshots, PDFs, and spreadsheets into clean i18n delivery packs.

This repo contains a reusable AI skill for localization workflows. It is built for teams that need to:

- extract UI copy from raw product materials
- reuse or generate i18n keys
- translate and review copy with AI
- export ready-to-ship bundles for iOS, Android, Web, and CSV flows

## What It Handles

- Raw PRD bundles: Markdown, Word, text-based PDF, XLSX, CSV, JSON
- Visual evidence: screenshots, scanned PDFs, Figma exports
- Existing localization catalogs: iOS `.strings`, Android `strings.xml`, JSON, CSV
- Delivery outputs: manifest JSON, CSV, Web/App JSON, iOS `.strings`, Android `strings.xml`

## Repo Structure

```text
.claude/agents/
skills/i18n-delivery-pipeline/
```

- `skills/i18n-delivery-pipeline` is the skill itself
- `.claude/agents` contains the helper agents used by the workflow

## Install Into Another Workspace

From the target workspace root:

```bash
cp -R /path/to/this-repo/skills .
mkdir -p .claude/agents
cp /path/to/this-repo/.claude/agents/i18n-*.md .claude/agents/
```

Then reopen the workspace or restart your coding agent.

## Quick Start

### 1. Start From Raw Product Materials

If you only have a PRD bundle:

```bash
python3 skills/i18n-delivery-pipeline/scripts/ingest_artifacts.py ./prd-bundle --output /tmp/evidence.json
python3 skills/i18n-delivery-pipeline/scripts/extract_copy_candidates.py /tmp/evidence.json --output /tmp/copy-candidates.json
python3 skills/i18n-delivery-pipeline/scripts/build_manifest_stub.py /tmp/copy-candidates.json --task-mode new-build --target-locales en,zh-Hans,de --target-outputs manifest,json,ios,android --output /tmp/i18n-manifest.json
```

### 2. Start From Existing Localization Exports

If you already exported current strings:

```bash
python3 skills/i18n-delivery-pipeline/scripts/normalize_snapshot.py --input-dir ./exports --metadata ./context.csv --output /tmp/i18n-snapshot.json
python3 skills/i18n-delivery-pipeline/scripts/build_manifest_stub.py /tmp/i18n-snapshot.json --task-mode change-sync --target-locales en,zh-Hans,de --target-outputs manifest,json,ios,android --output /tmp/i18n-manifest.json
```

### 3. Run QA And Export

```bash
python3 skills/i18n-delivery-pipeline/scripts/qa_manifest.py /tmp/i18n-manifest.json --report /tmp/i18n-qa.json
python3 skills/i18n-delivery-pipeline/scripts/emit_delivery_bundle.py /tmp/i18n-manifest.json --out-dir /tmp/delivery-bundle
```

## How It Thinks

The workflow stays practical on purpose:

- structured text beats screenshots
- screenshots help with scene understanding, not source-of-truth text
- short ambiguous labels must ask for context
- high-risk copy stays conservative and human-gated
- exporters adapt one canonical manifest into multiple platform formats

## Validation

Run the built-in smoke checks:

```bash
python3 skills/i18n-delivery-pipeline/scripts/run_smoke_evals.py
```

## Good Fit

This skill is a good fit if your team has any of these problems:

- product managers create copy in PRDs instead of clean spreadsheets
- translation keys are easy to duplicate and hard to find
- screenshots and design files carry important context
- review quality is inconsistent
- multiple teams need one reusable i18n workflow
