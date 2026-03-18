# Decision Tables

## Source Priority Rule

When multiple sources exist for the same string, choose source text in this order:

1. structured copy list or approved source file
2. exported localization snapshot for the source locale
3. Markdown PRD, Word text, spreadsheet tables, or text-based PDF
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

## Key Strategy Rule

Infer key strategy in this order:

1. if the user or team explicitly requests a naming policy, honor it
2. if all entries already have stable keys and the task is not a rename, use `inherit`
3. if the team provides a naming template, use `template`
4. otherwise use `canonical`

## Fallback Policy

| Situation | Action |
| --- | --- |
| `new-build` without snapshot | continue, but skip high-confidence dedupe and reuse |
| `change-sync` or `dedupe` without snapshot | block and ask for the current catalog |
| ambiguous short label without context | continue in downgraded mode and mark for human review |
| medium/high-risk copy from OCR or vision only | require verified text before completion |
| export requested without target outputs | ask for outputs before export |
| locale coverage unclear | ask for target locales, otherwise keep only the source locale final |

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
