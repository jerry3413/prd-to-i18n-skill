# Eval Rubrics

## Why These Rubrics Exist

The goal of this eval pack is not to judge whether a translation is "nice." It is to catch the specific business failures that would make this skill unsafe or noisy in production:

- misclassifying `L1/L2/L3`
- reusing a key when a new key is safer
- failing to escalate risky or ambiguous content

## Normalized Prediction Contract

Predictions should use this structure per case:

```json
{
  "case_id": "change_l2_button_action_shift",
  "change_level": "L2",
  "reuse_decision": "review",
  "review_decision": "human-gate",
  "human_review_required": true,
  "must_ask_for_context": false,
  "reason_codes": ["action-shift", "l2-change"]
}
```

The scorer normalizes minor variations such as:

- `new_key` -> `new-key`
- `human_gate` -> `human-gate`
- lowercase `l2` -> uppercase `L2`

## Label Definitions

### `change_level`

- `L0`
  Structural-only changes such as punctuation, spacing, tag wrappers, or placeholder wrappers.
- `L1`
  Wording or tone shifts where user intent stays the same.
- `L2`
  Meaning stays close, but user expectation, action, or field semantics may shift.
- `L3`
  Scene, legal meaning, business promise, responsibility, or core action changes.

### `reuse_decision`

- `reuse`
  Safe to keep the existing key.
- `review`
  Do not auto-reuse; requires a review decision.
- `new-key`
  Build a new key instead of reusing the old one.

### `review_decision`

- `pass`
  Safe to continue without revision or human gate.
- `revise`
  The model should not pass this as-is; fix or clarify first.
- `human-gate`
  A business owner or required reviewer must explicitly confirm before completion.

## Reason Code Legend

Use reason codes for diagnostics, not as the only grading signal.

- `exact-context-match`
- `same-text-different-scene`
- `fuzzy-match`
- `reviewed-content-protection`
- `placeholder-wrapper-only`
- `placeholder-mismatch`
- `tone-shift`
- `action-shift`
- `l2-change`
- `l3-meaning-shift`
- `high-risk`
- `strict-length`
- `missing-context`
- `ambiguous-short-label`
- `low-confidence-evidence`
- `identity-verification`

## Critical Error Policy

Treat these as blocking failures even when overall accuracy looks good:

- predicting `L1` or `L2` when the gold label is high-risk `L3`
- predicting `reuse` for a case marked `review` or `new-key` in high-risk scenarios
- predicting `pass` when the gold label is `human-gate`
- failing to ask for context on ambiguous short labels with missing scene information

## How To Expand The Pack

When adding new cases:

1. Prefer real or lightly redacted product copy.
2. Add at least one edge-case tag.
3. Keep the gold labels narrow and explicit.
4. Add reason codes that explain the expected decision, not just the raw category.
5. Update thresholds only after multiple evaluation rounds, not after one lucky run.
