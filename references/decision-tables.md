# Decision Tables

## Source Priority Rule

When multiple sources exist for the same string, choose source text in this order:

1. structured copy list or approved source file
2. exported localization snapshot for the source locale
3. Markdown PRD, Word text, HTML/MHTML exports, spreadsheet tables, or text-based PDF
4. Figma export or other structured design text
5. user transcription
6. screenshot or scanned OCR

Use the highest-confidence source for `source_text`.
Use lower-confidence visual sources only to recover `screen`, `component`, and layout context.

If two text sources conflict:

- prefer the higher-confidence source
- keep the losing source in `source_evidence.artifacts`
- do not auto-complete medium- or high-risk copy until the conflict is resolved

## Mode Detection Rule

Infer the operating mode from the best available data:

| Condition | Mode | Effect |
| --- | --- | --- |
| only `key + source_text` | `basic` | allow key suggestions and draft translations only |
| existing translations or business context are present | `review` | allow stronger reuse and review decisions |
| placeholders or `length_limit` are present | `strict` | enforce placeholder and delivery-budget checks |

Precedence:

`strict` > `review` > `basic`

Do not ask the user to choose the mode unless they are explicitly configuring policy.

## Delivery Intent Rule

Treat the task as `delivery-intent` when the user is not merely asking for an ad hoc translation, but is trying to prepare localization for release, handoff, import, or team consumption.

Common signals:

- the input is a PRD, release note, Confluence export, Word spec, or PDF requirement bundle
- the user says things like `prepare i18n`, `多语言`, `本地化`, `交付`, `接入`, `上线`, `ship`, `handoff`, `release`, `import`, or `导出`
- the document itself describes supported locales, release scope, or platform rollout

If `delivery-intent` is inferred from raw materials instead of stated explicitly, confirm the goal with the user before moving from extraction into translation or export.

Treat `draft-only` and `release-ready` as internal labels. In user-facing conversation, ask in plain language whether the user wants a simple draft list of translatable copy or a final package for import or developer handoff.

When `delivery-intent` is true:

1. ask for the target languages
2. ask what kind of delivery content the user wants, such as a source-copy list, translation table, reviewer handoff, or import-ready package
3. ask for the file format or handoff format that the team needs
4. ask whether this area was localized before; if yes, request the old files or exports because they help avoid duplicate keys
5. if the user needs the output to match an existing internal system format, ask for a sample or template file

Only skip these questions when one of the following is also true:

- the user explicitly says `draft only`, `just translate`, `just extract copy`, or another phrase that clearly opts out of release-ready delivery
- the older localization files, delivery content type, and file format are already present in the provided files
- team defaults are already known in the workspace and are safe to apply

## PRD Translation Routing Rule

If the user asks to translate a PRD, PDF, Confluence export, or spec, do not assume they mean localization delivery.

First confirm whether they want:

1. whole-document translation
2. extraction of user-facing copy for localization delivery

Keep the request inside this skill either way:

- if they choose whole-document translation, ask for the target language and continue in the document-translation branch
- if they choose localization delivery, continue in the localization-delivery branch
- if they do not choose yet, block before heavy extraction

For ambiguous requests such as `翻译我的PRD` or `translate my PRD`:

- do not default to whole-document translation
- do not ask for the target language first
- do not start document translation or localization extraction until the scope question is answered

## Key Strategy Rule

Infer key strategy in this order:

1. if the user or team explicitly requests a naming policy, honor it
2. if all entries already have stable keys and the task is not a rename, use `inherit`
3. if the team provides a naming template, use `template`
4. otherwise use `canonical`

## Fallback Policy

| Situation | Action |
| --- | --- |
| request appears to be PRD/spec translation but the scope is still ambiguous | block and clarify whether the user wants whole-document translation or localization copy extraction |
| ambiguous PRD/spec translation where the user did not choose a path yet | do not default to full-document translation; ask the scope question first |
| document-translation request without target language | block and ask for the target language |
| document-translation request with scope confirmed | continue with document translation and do not ask localization-only delivery questions |
| html or mhtml raw source is provided | ingest it directly as structured text; if cleanup is needed, describe it as a short cleanup pass rather than exposing DOM or parser details |
| raw-material request before the goal is confirmed | allow only lightweight preflight checks such as file type, page count, or whether text appears selectable; do not run full extraction, OCR, candidate building, or manifest generation yet |
| `new-build` without older localization files and request is draft-only | continue, but skip high-confidence dedupe and reuse |
| raw-material request where draft-only vs release-ready is still unclear | block and confirm the goal first |
| final delivery request without target languages | block and ask for the target languages first |
| final delivery request without delivery content type | block and ask whether the user wants a source-copy list, translation table, reviewer handoff, or import-ready package |
| final delivery request without file format | block and ask for the file format or handoff format |
| final delivery request that must match an internal system, but no sample/template was provided | block and ask for a sample or template |
| final delivery request with missing delivery details | do not default to CSV, JSON, or any other output format |
| `new-build` without older localization files and request looks like release prep | continue, but state that duplicate-key detection will be lower confidence |
| `change-sync` or `dedupe` without snapshot | block and ask for the current catalog |
| ambiguous short label without context | continue in downgraded mode and mark for human review |
| medium/high-risk copy from OCR or vision only | require verified text before completion |
| export requested without target outputs | ask for outputs before export |
| release-intent request without target outputs or handoff standard | block and ask for target outputs before final translation/export work |
| locale coverage unclear | ask for target locales, otherwise keep only the source locale final |

## Draft Result Presentation Rule

When the user asked for a draft copy list or draft translation output:

- if the result set is small, show it directly in the conversation first
- create a file only when the user asked for one, the result is too large for chat, or the next workflow step needs a saved artifact

## Human Gate Rule

Require human review when any of these are true:

- `risk_level` is `high`
- `change_level` is `L2` or `L3`
- `existing_match.status` is `fuzzy`, `conflict`, or `ambiguous`
- source evidence is low-confidence for medium- or high-risk copy
- placeholders are unresolved or platform mappings are incomplete for required outputs
- strict length constraints still fail after one revision
- the relevant owner must explicitly approve the copy

## Batch Limits

Use these defaults unless the manifest explicitly overrides them:

- `max_entries_per_slice = 50`
- `revision_loop_limit = 2`

If a safe parallel group exceeds `max_entries_per_slice`:

1. split by `screen`
2. then split by risk level
3. then chunk by entry count

Never parallelize unresolved high-risk entries, even if the batch is small.
