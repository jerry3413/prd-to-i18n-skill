---
name: i18n-delivery-pipeline
description: "Handle PRD, spec, and localization requests for app, web, and backend teams. Use when Codex needs to work from raw product materials such as PRDs, Confluence exports, Word files, PDFs, spreadsheets, screenshots, or Figma exports and must first determine whether the user wants full-document translation or a UI-copy localization package; then either translate the document or extract candidate user-facing copy, normalize exported localization snapshots or API results, recommend key reuse versus new keys, classify changes and release risk, generate or review translations, and emit delivery bundles such as manifest JSON, CSV, iOS .strings, Android strings.xml, or Web/App JSON."
---

# I18n Delivery Pipeline

## Overview

Turn fragmented PRD and spec inputs into either a translated document or one canonical i18n manifest and a release-ready delivery bundle. Treat API access as optional: the default operating mode is exported snapshot mode, with API mode as an adapter on top of the same workflow.

This skill is the front door for ambiguous PRD and spec translation requests. First decide whether the user wants:

- full-document translation
- localization delivery from user-facing copy

Use the document-translation path when the user wants the whole document translated. Use the localization path only when the user wants copy extraction, i18n packaging, or release handoff.

## Keep It Foolproof

Optimize for the simplest possible user interaction:

- infer the task mode from what the user already provided
- do not ask the user to choose internal modes or naming policies unless policy is the task
- accept one export folder before asking for explicit file descriptors
- ask for one blocking item at a time
- when the request starts from a raw PRD, PDF, Word doc, Confluence export, or spec bundle, ask in plain language what outcome the user wants before any heavy extraction, OCR, or manifest work
- if the request sounds like "translate my PRD" or another ambiguous spec-translation ask, first ask the user which path they want; do not default to whole-document translation or localization delivery on their behalf
- if the user wants the whole document translated, stay in this skill and run the document-translation path instead of forcing localization-only questions
- explain practical consequences in plain language instead of leading with internal jargon
- do not tell the user you need to "lock the goal", "start heavy processing", or other internal workflow phrases; just ask how they want you to handle the file
- do not narrate internal extraction heuristics such as whether the file looks like paragraphs, tables, or screenshot notes; only tell the user whether you can extract directly or need a short cleanup pass first
- if a draft copy result is small, show it directly in the conversation first; only create a file when the user asks for one or the result is large enough to need it

User-facing defaults:

- PRD/spec translation request -> clarify document translation vs localization delivery
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
   - `document-translation`
   - `new-build`
   - `change-sync`
   - `dedupe`
   - `translation-fix`
   - `export-only`
   Ask only for missing blocking inputs.
   For raw PRD/PDF/Word/spec requests, first clarify whether the user wants:
   - full document translation
   - localization copy extraction and delivery
   If the user already says `多语言`, `i18n`, `本地化`, `交付`, `导出`, `handoff`, or another clearly delivery-oriented phrase, do not ask the document-vs-localization split again. Go straight into the localization-delivery branch.
   If the user confirms full-document translation, collect:
   - the target language
   - the preferred output form only if the user cares about the final shape; otherwise default to a complete translated version that follows the source structure
   Then translate the document from the highest-confidence text source and stop. Do not ask localization-only delivery questions such as old localization files, import package type, or app resource formats.
   If the user confirms localization delivery, then ask in plain language whether they want:
   - a simple draft list of translatable copy
   - a final localization package that the team can import or hand to developers
   If the user's own wording already clearly implies final delivery, such as `交付多语言`, `提交多语言翻译`, `给研发`, `导入`, or `handoff`, skip the draft-vs-final question and go straight to the bundled delivery-contract question.
   Only after the user confirms the final delivery path should you require:
   - which product content is in scope when the PRD mixes more than one surface, such as app, web, seller, backend-admin, or other internal tools
   - the target languages
   - whether this area already has reusable keys, old translations, old handoff packages, or an API/export path you can query before you freeze keys or make reuse claims
   - the final handoff shape the team actually needs, including both what kind of package it is and what fields or files it must contain; a carrier label such as JSON, CSV, or XLSX is not enough when the team expects a specific field layout
   - a sample or template whenever the team needs the output to match an existing internal system format or old import schema
   The files or API themselves are not a default blocker, but the user's answer about whether reusable history exists is required before you freeze the key plan.
   When more than one of those delivery details is still missing, ask for them in one bundled delivery-contract question instead of splitting them into separate turns.
   If the user provides one platform's historical snapshot and also confirms the copy is shared across platforms, use that snapshot as a semantic dedupe aid. Only require another platform's historical files when the user explicitly needs platform-specific key continuity or platform-specific output mapping.
   If the PRD clearly mixes more than one product surface, do not guess which ones belong to this release. Ask the user which surfaces this delivery should cover before you freeze the manifest or create keys.
   After the user picks the final delivery path, do not continue into extraction or output generation until the required delivery details are answered.
   A bare answer such as `JSON`, `CSV`, or `XLSX` does not settle the final delivery contract unless the user explicitly accepts the built-in default exporter shape.
   If the user's first answer only covers part of the delivery contract, ask for the remaining missing items together in one follow-up instead of serializing them into one-question-per-turn.
   Before that question is answered, allow only lightweight preflight checks such as file type, page count, or whether the document appears to contain selectable text. Do not run full text extraction, OCR, copy-candidate extraction, or manifest building yet.
   The first substantive reply for raw materials must contain the goal-confirmation question before any suggestion that you are about to extract, translate, or generate output files.
   In user-facing replies, describe the task in plain language instead of requiring the user to know the mode name.
2. Collect the source artifacts.
   For `new-build` and `change-sync`, require a PRD, a copy list, or another reliable source of changed text.
   For `translation-fix`, `dedupe`, and `export-only`, do not require a PRD when the task can be completed safely without it.
   If the user confirms the task is a final delivery request rather than a simple draft, also collect:
   - the target languages
   - the target outputs or handoff standard for final delivery
   - whether reusable history exists, and whether it comes from files, export snapshots, or an API adapter
   - a sample or template file if the final package must match the team's existing schema
   Apply the source-priority rule from [references/decision-tables.md](references/decision-tables.md).
   Accept raw source bundles such as:
   - Markdown or text PRDs
   - HTML or Confluence `.mhtml` exports
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
   Do not create PRD-specific or version-specific generator scripts as the declared release path. If the missing capability is generic, improve the shared bundled scripts instead. Use one-off local helpers only for short inspection, not as the final workflow contract.
5. Ingest raw PRD artifacts when the user does not already have a structured copy list.
   Read [references/artifact-ingestion.md](references/artifact-ingestion.md).
   Run `scripts/ingest_artifacts.py` on mixed raw materials such as Word, Markdown, HTML, MHTML, PDF, XLSX, CSV, JSON, or screenshots.
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
   - `surface`
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
   For final delivery, do not freeze the key plan until the user has answered whether reusable history exists for this area, and whether it comes from files, exports, or an API path.
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
   For final delivery, the user-facing response must make the review step visible. State what was reviewed, what assumptions remain, and what items were excluded or left pending. Do not hide those facts only in generated files.
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
   If the target languages, delivery content type, old-file status, or file format are still unknown, do not emit delivery files and do not silently default to CSV, JSON, or any other format.
   Stop at a candidate list or draft manifest only and say the delivery contract is not settled yet. If that draft result is small, show it inline before creating any file.
   If the user needs a custom team format and no sample or template was provided, do not claim the output is final delivery-ready.
   Do not treat a carrier-only request such as `JSON` or `CSV` as a settled team handoff format unless the user explicitly accepts the skill's built-in default export profile.

## Apply The Policy

- Ask for more context when `background`, `intent`, or screenshot evidence is missing for ambiguous copy. If the user cannot provide it, continue in `basic` mode and mark the entry as review-required.
- Treat `L0` as QA-only.
- Treat `L1` as keep-key plus retranslate plus AI review.
- Treat `L2` as AI recommendation plus human confirmation.
- Treat `L3` as new key plus deprecate or inactivate the old key.
- Auto-escalate when placeholders are ambiguous, terminology conflicts, or length is strict.
- If a raw-material request never confirmed whether the user wants a simple draft or a final delivery package, stop and clarify the goal before heavy extraction or before claiming final translation or delivery output.
- If the user wants the whole PRD or whole PDF translated as a document, keep the work in this skill, ask for the target language, and stay out of the localization-delivery path.
- If a raw material needs preprocessing before extraction, describe it as a short cleanup pass instead of exposing parser, table-shape, or DOM-structure details.
- If a draft copy list is small and the user did not ask for a file, present it inline first and offer to save it only if they want to continue.
- If the source material mixes multiple surfaces and the user has not confirmed which ones belong to this delivery, stop and ask before final translation, key creation, or export.

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
