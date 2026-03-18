# Copy Extraction Rules

Use copy extraction when the user does not already have a structured copy list.

## Extraction Objective

Produce conservative `copy-candidates.json` entries that are safe enough to become a manifest skeleton.

Every candidate should aim to include:

- `source_text`
- `screen`
- `component`
- `intent`
- `background`
- `source_evidence`
- optional `screenshot_ref`

## Extract First, Ask Later

Extract automatically only when the copy is explicit.

Good signals:

- a table column explicitly labeled as copy, title, button text, toast text, message, subtitle, or label
- a line such as `按钮文案: Continue`
- a sentence such as `展示文案为 "Ad limit reached today"`
- a bullet under a clearly copy-specific heading

Weak signals:

- long narrative paragraphs
- business flow descriptions without explicit UI wording
- screenshots without text confirmation

## What To Extract

Prefer these patterns:

1. structured rows from CSV, JSON, XLSX, or DOCX tables
2. label-value lines
3. quoted UI strings with explicit copy cues
4. short bullet lists under copy-specific headings

## What Not To Extract

Do not extract from:

- pure requirement prose that does not explicitly show user-facing wording
- acceptance criteria that describe behavior but not displayed text
- architecture notes
- backend-only instructions

Do not invent text such as:

- button labels that were never written
- toast strings implied by a flow description
- legal copy reconstructed from a screenshot fragment

## Context Recovery

Recover `screen`, `component`, and `background` in this order:

1. explicit row or field values
2. nearby label-value context
3. surrounding headings
4. attached or nearby image evidence

If context is still weak:

- keep the candidate
- leave missing fields blank if necessary
- rely on downstream review and follow-up questions

## Target Locale And Output Hints

Copy extraction may suggest target locales or outputs only when the source material states them explicitly, for example:

- `支持语言: 简中, 英文, 德语`
- `交付端: iOS, Android, Web`

These hints are advisory.
The final source of truth remains the manifest configuration or team defaults.

## Safety Rule

If a candidate is a short ambiguous label such as `Open`, `Continue`, or `Photos`, never treat extraction alone as enough context for release.
