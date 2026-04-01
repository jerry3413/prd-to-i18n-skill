# Coordinator Core

## Purpose

Use the main conversation as the workflow owner for clarification-heavy work.

The coordinator should:

- classify the request
- assess readiness
- ask only the smallest blocking question set
- explain downgrades in plain language
- route work to translation or review only after the manifest slice is stable

For exact fallback behavior, read [decision-tables.md](decision-tables.md).
For branch-matching follow-up wording, read [coordinator-examples.md](coordinator-examples.md) only when needed.

## Intake Algorithm

1. Classify the request as one of:
   - `document-translation`
   - `new-build`
   - `change-sync`
   - `dedupe`
   - `translation-fix`
   - `export-only`
   - ambiguous PRD/spec translation
2. Inventory what is already present:
   - raw PRD or spec
   - exported locale files or snapshot
   - screenshots, PDF, or Figma evidence
   - included surfaces when the request mixes more than one surface
   - target languages
   - reusable-history status
   - handoff shape
   - sample or template when the team needs a fixed schema
3. Mark each missing item as either:
   - blocking
   - non-blocking but quality-reducing
4. Ask only for blocking items.
5. Stop before heavy extraction when a blocking scope decision is still unresolved.
6. Delegate only after the slice no longer depends on user clarification.

## Blocking Rules

Treat these as blocking:

- no confirmed path yet for an ambiguous PRD/spec translation request
- no target language yet for whole-document translation
- no target languages yet for final delivery
- no reusable-history status yet for final delivery
- no confirmed handoff shape yet for final delivery
- no current snapshot yet for `change-sync` or `dedupe`
- no scene context yet for ambiguous short labels when the answer would otherwise be trusted as final
- no verified text yet for medium- or high-risk content that came only from weak visual evidence

Treat these as non-blocking but quality-reducing:

- missing screenshots for low-risk copy when text context is already clear
- missing glossary for generic UI labels
- missing reusable history for `new-build` after the user already confirmed there is none

## Question Contract

- Use plain language. Do not ask users to choose `basic`, `review`, `strict`, `inherit`, `template`, or `canonical`.
- Ask at most one bundled blocking question per round unless the user explicitly asked for a checklist.
- Prefer concrete fields over open-ended prompts.
- Prefer one export folder over many explicit resource descriptors.
- If several delivery details are missing at once, collect them in one bundled delivery-contract question.
- If the user only wants a draft and the result is small, show it inline first.
- If text came from screenshots or scans, state the confidence limit plainly.

## Behavior Anchors

Minimal anchor 1:

- User: `translate this PRD`
- Ask: `Do you want the whole document translated, or only the product copy prepared for localization?`

Minimal anchor 2:

- User: `做多语言交付`
- Ask for: in-scope surfaces when mixed, target languages, reusable-history status, and the exact handoff shape in one bundled follow-up

## User-Facing Defaults

- PRD or copy list -> usually `new-build` or `change-sync`
- key plus one short string -> usually `translation-fix`
- manifest plus output request -> usually `export-only`
- export folder plus sidecar -> prefer the exported-resource path

## Do Not

- do not default ambiguous PRD translation into whole-document translation
- do not default a final output format from `JSON`, `CSV`, or `XLSX` alone
- do not narrate internal parser or DOM heuristics to the user
- do not keep asking one field per turn when one bundled question would resolve the blocker
