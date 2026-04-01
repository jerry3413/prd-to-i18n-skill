---
name: i18n-delivery-pipeline
description: "Route PRD, spec, and exported localization files into whole-document translation, draft copy extraction, or final localization delivery."
---

# I18n Delivery Pipeline

## Use When

Use this skill when the request starts from any of these:

- raw PRD or spec materials such as Markdown, Word, PDF, Confluence export, spreadsheet, screenshot, or Figma export
- exported locale resources such as iOS `.strings`, Android `strings.xml`, JSON, or CSV
- an ambiguous request that may mean either whole-document translation or localization delivery

## First Decision

For raw PRD, PDF, Word, Confluence, or screenshot bundles, ask what outcome the user wants before heavy extraction:

1. whole-document translation
2. a draft list of user-facing copy
3. a final localization package

## Critical Guardrails

- If a PRD or spec translation request is ambiguous, do not default. Ask whether the user wants whole-document translation or localization delivery.
- If the user already makes delivery intent explicit with phrases such as `多语言`, `i18n`, `本地化`, `交付`, `导出`, `handoff`, or `import`, skip the document-vs-localization split.
- If the user chooses whole-document translation, ask for the target language and stay out of localization-only questions.
- If the user chooses final delivery, do not start extraction, key creation, translation, or export until the delivery contract is confirmed.
- A carrier-only answer such as `JSON`, `CSV`, or `XLSX` is not a confirmed handoff shape.
- If the request is high-risk, context-poor, or ends in `human-gate`, do not present the result as fully finalized.

## Runtime State Map

Use the smallest relevant reference set for the current state:

1. `Intake`
   Read [coordinator-core.md](references/coordinator-core.md).
   Read [coordinator-examples.md](references/coordinator-examples.md) only when you need branch-matching follow-up phrasing.
2. `Disambiguation and fallback`
   Read [decision-tables.md](references/decision-tables.md).
3. `Input and capability handling`
   Read [input-contract.md](references/input-contract.md) for package shape.
   Read [capability-routing.md](references/capability-routing.md) for PDFs, screenshots, scans, OCR, or vision paths.
4. `Artifact processing`
   Read [artifact-ingestion.md](references/artifact-ingestion.md) for raw bundles.
   Read [copy-extraction-rules.md](references/copy-extraction-rules.md) for candidate extraction.
   Read [manifest-schema.md](references/manifest-schema.md) before building or editing the canonical manifest.
5. `Review and release gating`
   Read [review-policy.md](references/review-policy.md).
6. `Parallel execution after the slice is frozen`
   Read [agent-orchestration.md](references/agent-orchestration.md).

## Minimal Decision Anchors

- Ambiguous request example:
  `translate this PRD` -> ask whether to translate the whole document or only the product copy for localization.
- Explicit delivery example:
  `做多语言交付` -> ask for included scope when the source mixes surfaces, target languages, reusable-history status, and the final handoff shape in one bundled follow-up.

## Artifact Flow

- Raw non-text or mixed bundles:
  run `scripts/route_capabilities.py` first when PDFs, screenshots, or scans are present.
- Raw artifact path:
  `scripts/ingest_artifacts.py` -> `scripts/extract_copy_candidates.py` -> `scripts/build_manifest_stub.py`
- Exported resource path:
  `scripts/normalize_snapshot.py` -> `scripts/build_manifest_stub.py`
- Finalized manifest path:
  `scripts/plan_execution.py` -> `scripts/qa_manifest.py` -> `scripts/emit_delivery_bundle.py`

## Working Rules

- Prefer one export folder over explicit resource descriptors until auto-discovery is insufficient.
- Prefer one bundled delivery-contract question over serial one-field turns when several delivery details are missing.
- If the result is a small draft list, show it inline first unless the user asked for a file.
- Do not create PRD-specific generator scripts as the official workflow. If a generic capability is missing, improve the shared scripts instead.
