# Artifact Ingestion

Use artifact ingestion when the user has raw project materials instead of a ready copy list.

## Supported Raw Formats

Prefer these as first-class inputs:

- Markdown or plain text PRDs
- HTML or Confluence `.mhtml` exports
- Word `.docx`
- text-extractable PDF
- CSV or JSON tables
- Excel `.xlsx`

Accept these as supporting evidence:

- screenshots
- scanned PDFs
- Figma exports

## Ingestion Goal

Convert mixed raw files into one `evidence.json` package before copy extraction.

If the source is HTML or MHTML, extract the main page text inside the ingestion step. Do not rely on an ad hoc external conversion script as the normal path.

The evidence package should preserve:

- file path
- artifact kind
- whether reliable text was extracted
- ordered text blocks
- nearby or embedded image references
- extraction mode and confidence

## Confidence Rules

- `markdown`, `docx`, `csv`, `json`, `xlsx`
  Treat as structured text with high confidence when parsing succeeds.
- `pdf-text`
  Treat as medium confidence because reading order can still drift.
- `screenshot`, scanned PDF, image-only exports
  Treat as visual evidence, not source-of-truth text.

## Image Handling

Images help with scene understanding, not with authoritative source text.

Use images to recover or confirm:

- `screen`
- `component`
- visual hierarchy
- likely interaction context

Do not use images alone to finalize medium- or high-risk text.

## Text And Image Matching

Use structural matching before semantic guessing:

- `docx`
  Match embedded images to the nearest paragraph or table row in document order.
- `xlsx`
  Match drawing anchors to the nearest worksheet row.
- `pdf`
  Keep page-level evidence unless a deterministic text anchor exists.
- standalone screenshots
  Keep them as `screen-level evidence` unless another artifact gives a stronger string-level anchor.

## Non-Goals

Do not treat ingestion as free-form interpretation.

Ingestion should not:

- invent missing copy
- decide key reuse
- guess release risk from business intent alone
- infer target locales unless they are explicitly written in the source material

Keep internal structure diagnosis internal. It is fine to decide internally that a file needs a short cleanup pass before copy extraction, but user-facing replies should only say whether extraction can continue directly or needs a quick cleanup first.

## Practical Recommendation

If the team has mixed materials, run:

`python3 scripts/ingest_artifacts.py ./prd-bundle --output /tmp/evidence.json`

Then feed the result into:

`python3 scripts/extract_copy_candidates.py /tmp/evidence.json --output /tmp/copy-candidates.json`
