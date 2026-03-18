---
name: i18n-delivery-pipeline
description: Orchestrate PRD-to-localization delivery workflows for app, web, and backend teams. Use when Codex needs to ingest raw PRD bundles such as Markdown, Word, PDF, XLSX, screenshots, or Figma exports; extract candidate copy and context; normalize exported localization snapshots or API results; recommend key reuse versus new keys; classify changes and release risk; generate or review translations; and emit delivery bundles such as manifest JSON, CSV tables, iOS .strings, Android strings.xml, or Web/App JSON.
---

# I18n Delivery Pipeline

## Overview

Turn fragmented localization inputs into one canonical i18n manifest and a release-ready delivery bundle. Treat API access as optional: the default operating mode is exported snapshot mode, with API mode as an adapter on top of the same workflow.

## Keep It Foolproof

Optimize for the simplest possible user interaction:

- infer the task mode from what the user already provided
- do not ask the user to choose internal modes or naming policies unless policy is the task
- accept one export folder before asking for explicit file descriptors
- ask for one blocking item at a time
- when the request starts from a raw PRD, PDF, Word doc, or spec bundle, ask in plain language what outcome the user wants before any heavy extraction, OCR, or manifest work
- explain practical consequences in plain language instead of leading with internal jargon

User-facing defaults:

- PRD or copy list -> `new-build` or `change-sync`
- key plus one string -> `translation-fix`
- manifest or output request -> `export-only`
- export folder plus optional sidecar -> preferred non-API input path

## Start With Intake

Use the coordinator protocol in the main conversation first. The main thread is the workflow owner: it guides the user into the workflow, classifies the request, detects missing inputs, and asks only the minimum blocking questions before any translation or review work begins.

- Read [references/decision-tables.md](references/decision-tables.md) before making source-priority, fallback, or human-gate decisions.
- Read [references/coordinator-intake.md](references/coordinator-intake.md).
- Treat `assets/helper-agents/i18n-coordinator.md` as an optional project-level helper template, not the owner of nested delegation.
- Keep intake in the foreground whenever the workflow may need user clarification.

## Run The Workflow

1. Run readiness intake.
   Classify the request into one of:
   - `new-build`
   - `change-sync`
   - `dedupe`
   - `translation-fix`
   - `export-only`
   Ask only for missing blocking inputs.
   For raw PRD/PDF/Word requests, first ask in plain language whether the user wants:
   - a simple draft list of translatable copy
   - a final localization package that the team can import or hand to developers
   Only after the user confirms the final delivery path should you require the current localization baseline and target outputs.
   Before that question is answered, allow only lightweight preflight checks such as file type, page count, or whether the document appears to contain selectable text. Do not run full text extraction, OCR, copy-candidate extraction, or manifest building yet.
   In user-facing replies, describe the task in plain language instead of requiring the user to know the mode name.
2. Collect the source artifacts.
   For `new-build` and `change-sync`, require a PRD, a copy list, or another reliable source of changed text.
   For `translation-fix`, `dedupe`, and `export-only`, do not require a PRD when the task can be completed safely without it.
   If the user confirms the task is a final delivery request rather than a simple draft, also collect:
   - the current localization baseline for dedupe and reuse
   - the target outputs or handoff standard for final delivery
   Apply the source-priority rule from [references/decision-tables.md](references/decision-tables.md).
   Accept raw source bundles such as:
   - Markdown or text PRDs
   - Word `.docx`
   - text-based PDFs
   - spreadsheets such as `.xlsx`, CSV, or JSON
   Accept PDFs and screenshots as source evidence, but record how text was obtained:
   - direct text extraction from a text-based PDF
   - vision-only reading from a scanned PDF or screenshot
   - user-provided transcription
   Accept one or more localization corpora:
   - exported iOS `.strings`
   - exported Android `strings.xml`
   - CSV or JSON catalogs
   - API adapter output
   - a manual context sidecar keyed by `key`
3. Choose the operating mode.
   Apply the mode-detection and key-strategy rules from [references/decision-tables.md](references/decision-tables.md).
4. Route around capability limits.
   Read [references/capability-routing.md](references/capability-routing.md).
   Run `scripts/route_capabilities.py` when the inputs include PDFs, screenshots, scanned documents, or any non-text source.
   Decide among:
   - `text-first`
   - `native-vision`
   - `vision-extension`
   - `local-ocr`
   - `manual-fallback`
5. Ingest raw PRD artifacts when the user does not already have a structured copy list.
   Read [references/artifact-ingestion.md](references/artifact-ingestion.md).
   Run `scripts/ingest_artifacts.py` on mixed raw materials such as Word, Markdown, PDF, XLSX, CSV, JSON, or screenshots.
   Preserve text blocks, image evidence, extraction confidence, and ordered structure in one evidence package.
6. Extract copy candidates.
   Read [references/copy-extraction-rules.md](references/copy-extraction-rules.md).
   Run `scripts/extract_copy_candidates.py` when the user provided a PRD bundle instead of a ready copy list.
   Extract only explicit user-facing strings and recover `screen`, `component`, `intent`, and `background` conservatively.
7. Normalize the current localization corpus.
   Run `scripts/normalize_snapshot.py` before reasoning about duplicates or changes.
   Read [references/input-contract.md](references/input-contract.md) whenever the exported shape is unfamiliar.
   Prefer the simple path first:
   - `python3 scripts/normalize_snapshot.py --input-dir ./exports --metadata ./context.csv --output /tmp/i18n-snapshot.json`
   Use explicit `--resource kind=...,path=...` descriptors only when auto-discovery is not enough.
8. Build or update the canonical manifest skeleton.
   Run `scripts/build_manifest_stub.py` after normalization whenever you need a deterministic manifest starting point.
   The manifest builder also accepts a copy-candidates package when the task starts from raw PRD materials.
   Use [references/manifest-schema.md](references/manifest-schema.md) as the source of truth.
   Fill or preserve these fields for every candidate entry:
   - `screen`
   - `component`
   - `source_text`
   - `intent`
   - `background`
   - `source_evidence`
   - `screenshot_ref`
   - `key_candidate`
   - `existing_match`
   - `change_level`
   - `message_format`
   - `placeholders`
   - `length_limit`
9. Decide reuse versus creation.
   Apply [references/review-policy.md](references/review-policy.md) and the human-gate rule from [references/decision-tables.md](references/decision-tables.md).
   Only auto-reuse when `source_text + intent + context` match exactly.
   Route fuzzy matches to review.
   Never let low-confidence automation overwrite completed high-risk content.
10. Plan execution before delegating.
   Read [references/agent-orchestration.md](references/agent-orchestration.md).
   Run `scripts/plan_execution.py` on the manifest to decide what stays serial and what can run in parallel.
   Respect `max_entries_per_slice` and `revision_loop_limit`.
11. Run the generation loop.
   Keep orchestration in the main conversation.
   Separate generation from review:
   - translation pass: use the `i18n-translator` subagent for prepared manifest slices
   - review pass: use the `i18n-reviewer` subagent for release gating
   If review fails, revise only the affected entries and re-run review.
12. Run deterministic QA.
   Run `scripts/qa_manifest.py` before export or API writeback.
   Expect QA to catch at least:
   - duplicate keys
   - missing required locale coverage
   - placeholder mismatches or missing platform mappings for required outputs
   - length overflow against declared budgets
   - high-risk entries missing human review routing
   If you changed prompts, orchestration, or policy logic, also run the curated model eval pack before calling the skill release-ready.
13. Emit delivery bundles.
   Run `scripts/emit_delivery_bundle.py` to generate manifest JSON, flat CSV, Web/App JSON, iOS `.strings`, and Android `strings.xml`.
   Keep canonical placeholders in the manifest and let exporters adapt them to platform-native formats.
   If target outputs are still unknown, stop at a draft manifest or CSV and say the delivery contract is not frozen yet.

## Apply The Policy

- Ask for more context when `background`, `intent`, or screenshot evidence is missing for ambiguous copy. If the user cannot provide it, continue in `basic` mode and mark the entry as review-required.
- Treat `L0` as QA-only.
- Treat `L1` as keep-key plus retranslate plus AI review.
- Treat `L2` as AI recommendation plus human confirmation.
- Treat `L3` as new key plus deprecate or inactivate the old key.
- Auto-escalate when placeholders are ambiguous, terminology conflicts, or length is strict.
- If a raw-material request never confirmed whether the user wants a simple draft or a final delivery package, stop and clarify the goal before heavy extraction or before claiming final translation or delivery output.

## Use Large-Batch Tactics

For batches over roughly 40 strings or more than one screen:
- Lock the manifest skeleton first.
- Parallelize by role or screen only after the skeleton is stable.
- Give each worker raw artifacts, not your conclusions.
- Merge results only after QA passes.

When subagents are available, use separate workers for:
- engineering and snapshot normalization
- translation generation
- review and release gating

## Schedule Work Intelligently

Follow Anthropic's current guidance on prompt chaining, parallelization, evaluator-optimizer loops, and subagent orchestration:

- Keep work in the main conversation for shared-context phases such as intake, PRD interpretation, key strategy selection, and any step that needs rapid clarification.
- Chain agents serially when later work depends on earlier outputs or when you need a fixed pipeline you can inspect.
- Parallelize only after the manifest slice is frozen and the slices are independent.
- Prefer subagents over agent teams for this workflow because translators and reviewers usually return summaries to the coordinator rather than debating each other directly.
- Use agent teams only for unusually large cross-surface launches where workers must communicate across independent sessions.

### Auto-Serial Rules

Keep translation and review serial when any of these are true:

- `risk_level` is `high`
- `change_level` is `L2` or `L3`
- placeholders exist or are ambiguous
- `length_limit.mode` is `strict`
- `existing_match.status` is `fuzzy` or conflict-like
- context is incomplete
- a human checkpoint is mandatory before completion

### Auto-Parallel Rules

Allow translation in parallel only when all of these are true:

- manifest skeleton is frozen
- entries are grouped into independent slices, usually by `screen`
- `risk_level` is `low` or `medium`
- `change_level` is `L0` or `L1`
- context is complete
- placeholders are absent and no strict length budget applies

Allow review in parallel only for slices that already satisfied the parallel translation rules and do not require a high-risk or human-blocking decision.

## Read The References

- [Coordinator Intake](references/coordinator-intake.md)
- [Decision Tables](references/decision-tables.md)
- [Artifact Ingestion](references/artifact-ingestion.md)
- [Capability Routing](references/capability-routing.md)
- [Copy Extraction Rules](references/copy-extraction-rules.md)
- [Evaluation](references/evaluation.md)
- [Eval Rubrics](references/eval-rubrics.md)
- [Input Contract](references/input-contract.md)
- [Multimodal Inputs](references/multimodal-inputs.md)
- [Manifest Schema](references/manifest-schema.md)
- [Review Policy](references/review-policy.md)
- [Agent Orchestration](references/agent-orchestration.md)
- [Vision Extension](references/vision-extension.md)

## Use The Scripts

- `scripts/normalize_snapshot.py`
- `scripts/ingest_artifacts.py`
- `scripts/extract_copy_candidates.py`
- `scripts/build_manifest_stub.py`
- `scripts/route_capabilities.py`
- `scripts/plan_execution.py`
- `scripts/qa_manifest.py`
- `scripts/emit_delivery_bundle.py`
- `scripts/run_smoke_evals.py`
- `scripts/export_model_eval_csv.py`
- `scripts/score_model_evals.py`

## Start From Templates

Reuse the sample files in `assets/` when the user has only exported resource files and an informal context list.
Use `assets/sample-prd.md` as a minimal raw-PRD example for the new ingestion and extraction stages.
If the project supports Claude Code subagents, keep the main conversation as coordinator and use `i18n-translator` plus `i18n-reviewer` as leaf workers. Optional project-level agent templates live in `assets/helper-agents/` if you want to copy them into `.claude/agents/`.
Use the MCP template in `assets/vision-mcp-template.json` only as a starting point. Keep real API keys in environment variables or local scope, not inside the skill.
