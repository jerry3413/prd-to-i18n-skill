# Vision Extension

## Goal

Support a third-party vision or OCR provider as an optional extension, not as a required dependency.

The extension should help extract text and visual cues from screenshots, scanned PDFs, or image-heavy exports. It should not become the authority on key strategy, change classification, translation quality, or release gating.

## V1 Scope

V1 should provide:

- a routing rule that knows when to try the extension
- a generic configuration contract
- a safe key-handling policy
- a template for MCP-based integration

V1 should not hard-code any one provider.

## What The Extension Is Responsible For

- OCR or text extraction
- layout hints
- image-region interpretation
- confidence notes when supported

## What The Extension Is Not Responsible For

- deciding whether to reuse or create a key
- translating the final copy
- approving release readiness
- overriding human review gates

## Recommended Integration Pattern

Prefer a remote HTTP MCP server when the provider is cloud-based. Prefer local stdio tooling when the provider is a local OCR stack.

Keep the integration generic:

- provider URL
- auth header or env-backed secret
- optional model or mode setting
- optional timeout

## Secret Handling Rules

- Never store real API keys in `SKILL.md`, references, assets, manifests, or PRDs.
- Use environment variables such as `${VISION_API_KEY}`.
- For personal or experimental setups, prefer local scope.
- For team-shared setup, commit only placeholder-based `.mcp.json` configuration.

## Suggested Fields For A Vision Provider Contract

- `provider_name`
- `transport`
- `url` or `command`
- `auth_env_var`
- `supports_pdf`
- `supports_images`
- `returns_confidence`
- `max_file_size_mb`
- `notes`

## Failure Policy

If the extension is configured but unavailable:

- fall back to `local-ocr` if available
- otherwise fall back to `manual-fallback`
- keep the user informed that extraction confidence decreased

If the extension returns low-confidence output:

- keep the extracted text as draft evidence
- require confirmation for ambiguous, medium-risk, or high-risk items

## Recommended Artifacts

- `assets/vision-mcp-template.json`
- `scripts/route_capabilities.py`
- optional provider-specific setup instructions outside the core skill, if a team later standardizes on one provider
