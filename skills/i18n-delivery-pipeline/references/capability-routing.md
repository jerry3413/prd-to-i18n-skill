# Capability Routing

## Purpose

Do not assume every user or runtime has the same multimodal abilities.

Before processing PDFs, screenshots, or scanned documents, route the request through a capability check. The goal is to choose the safest path that the current environment can actually support.

## Capability Tiers

- `text-first`
  Structured text is available: Markdown, Word text, selectable PDF text, CSV, JSON, XLSX tables, iOS `.strings`, or Android `strings.xml`.
- `native-vision`
  The current model/runtime can directly inspect images or PDFs.
- `vision-extension`
  The runtime can call an external vision or OCR service through a configured MCP server or similar adapter.
- `local-ocr`
  The runtime cannot inspect images directly but can use deterministic local tooling such as OCR or PDF text extraction.
- `manual-fallback`
  None of the above is available. The user must provide a minimal context packet manually.

## Default Routing Rules

1. If structured text already exists, choose `text-first`.
2. If the source is a text-based PDF and reliable extraction is possible, still prefer `text-first`.
3. If the input is mixed but includes reliable structured text, still choose `text-first` and use image evidence only for disambiguation.
4. If the source is image-heavy and the runtime has native vision, choose `native-vision`.
5. If native vision is unavailable but a trusted external vision service is configured, choose `vision-extension`.
6. If neither native vision nor external vision exists but local OCR is available, choose `local-ocr`.
7. Otherwise choose `manual-fallback`.

## Risk Overrides

Even when a vision path is available:

- use text-first when exact legal, pricing, identity, or compliance wording must be preserved
- escalate medium-risk copy if the extracted text is uncertain
- never auto-complete high-risk copy from weak visual evidence alone

## Recommended Questions

When the path is unclear, the coordinator should ask:

- whether the PDF text is selectable
- whether the current environment supports image or PDF understanding
- whether the team has configured an external vision/OCR integration
- whether a local OCR tool is available

Keep the question count low. If one answer is enough to choose a path, stop there.

## Output Contract

When `scripts/route_capabilities.py` runs, it should produce:

- `recommended_path`
- `confidence`
- `why`
- `blocking_requirements`
- `suggested_questions`
- `next_step`

## Practical Matrix

### Markdown, CSV, JSON, resource exports

- Route: `text-first`
- Confidence: `high`
- User follow-up: usually none

### Mixed package with structured text plus screenshots or PDFs

- Route: `text-first`
- Confidence: `high`
- User follow-up: use image evidence only to resolve ambiguous labels or confirm visual context

### Selectable PDF text

- Route: `text-first`
- Confidence: `medium` to `high`
- User follow-up: verify reading order if the layout is dense

### Screenshot or scanned PDF with native vision

- Route: `native-vision`
- Confidence: `medium`
- User follow-up: ask for minimal context on short or ambiguous labels

### Screenshot or scanned PDF with external vision service

- Route: `vision-extension`
- Confidence: `medium`
- User follow-up: confirm the extension is configured and trusted

### Screenshot or scanned PDF with local OCR only

- Route: `local-ocr`
- Confidence: `low` to `medium`
- User follow-up: confirm exact text for high-risk or long strings

### Screenshot or scanned PDF with no tooling

- Route: `manual-fallback`
- Confidence: `low`
- User follow-up: request `source_text + screen + component + background`

## Security Rules

- Treat external vision providers as optional adapters, not mandatory infrastructure.
- Never place real API keys in skill files, PRDs, manifests, or shared project defaults.
- Prefer environment variables.
- Prefer local scope when credentials are personal or sensitive.
- Use project scope only for shared configuration shells with secret placeholders.
