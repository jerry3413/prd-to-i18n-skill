# Manifest Schema

## Canonical Shape

Use one canonical JSON document as the system of record:

```json
{
  "manifest_version": "1.1",
  "source_locale": "en",
  "key_mode": "inherit",
  "task_mode": "new-build",
  "generated_at": "2026-03-17T00:00:00Z",
  "target_locales": ["en", "zh-Hans", "de"],
  "required_locale_coverage": ["en", "zh-Hans", "de"],
  "target_outputs": ["manifest", "csv", "json", "ios", "android"],
  "max_entries_per_slice": 50,
  "revision_loop_limit": 2,
  "entries": [
    {
      "key": "app_rewarded_ad_toast_daily_limit_reached",
      "key_candidate": "app_rewarded_ad_toast_daily_limit_reached",
      "screen": "rewarded_ad",
      "component": "toast",
      "intent": "inform_daily_ad_limit_reached",
      "source_text": "Ad limit reached today",
      "background": "Shown after the user taps watch ad but has already reached the daily cap.",
      "source_evidence": {
        "extraction_mode": "snapshot-export",
        "confidence": "high",
        "verified_text": true,
        "artifacts": [
          {
            "kind": "ios",
            "path": "/exports/en.strings"
          }
        ]
      },
      "screenshot_ref": "rewarded-ad-toast-01",
      "existing_match": {
        "status": "none",
        "matched_key": null,
        "confidence": 0.0
      },
      "change_level": "L3",
      "risk_level": "medium",
      "message_format": "plain",
      "placeholders": [],
      "length_limit": {
        "mode": "strict",
        "max_chars": 28
      },
      "translations": {
        "en": {
          "value": "Ad limit reached today",
          "status": "source"
        },
        "zh-Hans": {
          "value": "",
          "status": "pending"
        }
      },
      "audit": {
        "ai_review": "pending",
        "human_review_required": true,
        "owner": "growth-owner"
      }
    }
  ]
}
```

## Required Entry Fields

- `key`
- `source_text`
- `screen`
- `component`
- `intent`
- `background`
- `source_evidence`
- `translations`

## Required Top-Level Fields

- `manifest_version`
- `source_locale`
- `key_mode`
- `generated_at`
- `target_locales`
- `required_locale_coverage`
- `target_outputs`
- `entries`

## Recommended Entry Fields

- `key_candidate`
- `screenshot_ref`
- `existing_match`
- `change_level`
- `risk_level`
- `message_format`
- `placeholders`
- `length_limit`
- `audit`

## Recommended Top-Level Fields

- `task_mode`
- `max_entries_per_slice`
- `revision_loop_limit`

## Default Canonical Key Rule

When the team selects `canonical`, use:

`{surface}_{screen}_{component}_{intent}[_qualifier]`

Apply these rules:

- Use lowercase snake case.
- Prefer stable semantics over raw copy.
- Avoid transient UI wording in the key.
- Keep the surface short: `app`, `web`, `backend`.
- Add a qualifier only when it prevents collisions.
- Deprecate old keys instead of silently reassigning them.

Example:

- `app_identify_overlay_hint_align_coin`
- `app_rewarded_ad_toast_daily_limit_reached`
- `backend_identity_error_verification_required`

## Supported Delivery Outputs

- canonical `manifest.json`
- flat CSV table for import or audit
- Web/App locale JSON
- iOS `.strings`
- Android `strings.xml`

All exporters should read from the same manifest rather than re-deriving content from raw prompts.

Use `target_outputs` to declare which artifacts must be generated from this manifest.
Use `required_locale_coverage` to declare which locales must be populated before final export.

## Evidence And Placeholder Rules

Use `source_evidence` to preserve provenance across the workflow:

- `extraction_mode`
  One of `snapshot-export`, `pdf-text`, `vision`, `ocr`, or `user-transcribed`
- `confidence`
  One of `high`, `medium`, or `low`
- `verified_text`
  `true` when the exact source text has been confirmed
- `artifacts`
  File paths or descriptors that show where the text came from

Use `message_format` plus `placeholders` to preserve a platform-agnostic source string while still exporting platform-native resources.

Recommended canonical style:

- `message_format: "named-template"`
- translations use named placeholders such as `{count}`
- each placeholder declares platform mappings when needed

Example placeholder spec:

```json
{
  "name": "count",
  "type": "number",
  "canonical": "{count}",
  "ios": "%1$ld",
  "android": "%1$d",
  "web": "{count}"
}
```
