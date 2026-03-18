# Multimodal Inputs

## Supported Non-Text Inputs

The skill may receive:

- text-based PDFs
- scanned PDFs
- screenshots
- Figma exports

Treat these as evidence sources for copy extraction and context building, not as guaranteed ground truth.

## Extraction Modes

Record one extraction mode for every candidate string:

- `pdf-text`
  Use when the PDF has selectable text or a reliable text layer.
- `vision`
  Use when the content comes from screenshots, scanned PDFs, or image-heavy exports.
- `user-transcribed`
  Use when the user pasted or typed the text manually.

When possible, store the extraction method and a confidence note in the coordinator summary or manifest-side working notes.

## Reliability Rules

### Text-Based PDF

This is usually the safest non-Markdown source.

- Prefer direct text extraction over vision reading.
- Still verify headings, tables, and callouts because layout can scramble reading order.
- Confirm section boundaries before extracting many strings from a dense PRD.

### Screenshots And Scanned PDFs

These are helpful but lower-confidence.

- Use them to identify screen, component, visual hierarchy, and likely interaction context.
- Do not treat the text as perfectly reliable if the image is blurry, cropped, tiny, or partially occluded.
- For long strings or dense screens, prefer asking for a text export or manual list instead of trusting raw visual reading.

## When Image Or PDF Evidence Is Enough

You may proceed without extra questions when all of these are true:

- the visible text is legible
- the screen purpose is obvious
- the copy is low-risk
- no placeholder or strict-length rule depends on precise punctuation

## When To Ask For More

Ask for a text export, cropped screenshot, or manual transcription when any of these are true:

- the image is blurry or incomplete
- the same text could mean different things depending on the screen
- the content is high-risk
- the content contains variables, code snippets, markup, or numbers that must be exact
- the text is too long to trust vision-only extraction

## Insufficient Context Policy

If the user-provided scene description is weak, do not guess.

Use this decision tree:

1. If the copy is ambiguous but low-risk, ask for `screen`, `component`, and one-sentence `background`.
2. If the user cannot provide it, continue in `basic` mode and mark the entry `review-required`.
3. If the copy is medium-risk and ambiguity could change action or user expectation, hold final release and request clarification.
4. If the copy is high-risk, do not auto-complete. Require explicit context and a human checkpoint.

## Minimal Context Packet

When the user does not have a full sidecar, ask for only:

- `screen`
- `component`
- `background`

Optional but useful:

- screenshot
- owner
- length limit
- glossary term

## Example Clarifications

Good follow-up:

- “For this screenshot-derived label, please tell me which screen it is on, what UI component it belongs to, and what action happens when the user taps it.”
- “This PDF section looks like pricing copy. Please confirm whether this is user-facing text or an internal note.”

Bad follow-up:

- “Please explain the business.”
- “Can you give me more context?”
