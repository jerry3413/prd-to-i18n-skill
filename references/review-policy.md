# Review Policy

## Change Levels

- `L0`
  Treat structural-only edits as QA-only. This includes punctuation, spacing, HTML tags, or placeholder wrappers that do not change meaning.
- `L1`
  Keep the key. Retranslate and run AI review when tone or wording shifts slightly but the user intent stays the same.
- `L2`
  Ask for human confirmation when the meaning is close but may change user expectation, action, or flow interpretation.
- `L3`
  Create a new key and deprecate or inactivate the old one when scene, action, legal meaning, responsibility, or promise changes.

## Risk Levels

- `low`
  Buttons, labels, empty states, and non-critical hints. AI review may auto-complete.
- `medium`
  Guidance, operational prompts, and conversion copy. AI review passes first, then route to human sampling or owner review.
- `high`
  Payments, pricing, discounts, legal language, penalties, irreversible actions, risk control, identity verification, commitments, and disclaimers. Always require human confirmation.

## Auto-Escalate Triggers

Move an entry up one level when any of these are true:

- context is missing or ambiguous
- source text was extracted only from low-confidence visual evidence
- placeholders are missing, renamed, or reordered
- placeholder platform mapping is incomplete for the target export
- length is marked strict
- terminology conflicts with the glossary or prior approved content

## Reuse Rules

- `exact match`
  Auto-reuse only when `source_text + intent + context` align.
- `fuzzy match`
  Never auto-publish. Suggest reuse versus new key and route to review.
- `reviewed content protection`
  Do not let low-confidence automation overwrite approved high-risk content.

## Translation Loop

Run translation and review as separate passes:

1. Build a compact context packet for one screen or one batch.
2. Generate target locales.
3. Review for scene fit, business intent, terminology, placeholders, and length.
4. Revise only failed entries.
5. Run deterministic QA before export or writeback.

## Missing Context Rule

If `background` or `intent` is missing for ambiguous text, ask for it. If the user cannot supply it, continue only in downgraded mode and mark the entry as requiring human review.

## Visual Evidence Rule

If the source text came from a screenshot or scanned PDF and the text is hard to read, cropped, or context-poor:

- do not auto-complete medium- or high-risk entries
- ask for a clearer crop, text export, or manual transcription
- if the user cannot provide one, keep the output in draft or review-required state
