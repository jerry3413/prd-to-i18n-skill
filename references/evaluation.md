# Evaluation

## Why Evaluate This Skill

Anthropic's current guidance emphasizes defining success criteria and using evaluations to improve real behavior, not just prompt wording. For this workflow, the highest-value checks are:

- intake quality
- source-priority selection
- change classification
- reuse versus new-key decisions
- manifest skeleton completeness
- placeholder safety across platforms
- serial versus parallel routing

## V1.1 Smoke Eval Scope

Run `scripts/run_smoke_evals.py` for deterministic checks that should stay green:

1. raw artifact ingestion discovers Markdown, DOCX, and XLSX inputs
2. copy extraction recovers explicit candidate strings and explicit locale hints
3. capability routing chooses the expected path
4. execution planning keeps risky slices serial
5. execution planning parallelizes safe slices
6. input-dir normalization discovers common export files
7. manifest stub generation works from both copy-candidates packages and normalized snapshots
8. bundle export adapts canonical placeholders into iOS and Android formats

These are smoke tests, not full model evaluations.

## Model Eval Focus

The most important model-eval surfaces for this skill are:

- `L1` versus `L2` versus `L3` boundary judgment
- reuse versus review versus new-key decisions
- reviewer escalation quality, especially false negatives on human gates
- missing-context handling for ambiguous short labels
- reviewed-content protection for high-risk legacy copy

Use a curated pack with gold labels before calling the skill production-ready across teams.

## Curated Eval Pack

The skill now ships a curated pack at `assets/model-eval-pack.json`.

Each case includes:

- a realistic business scenario
- normalized input fields
- one or more expected labels
- reason codes for error analysis
- tags for suite and edge-case slicing

The current pack is organized around 3 suites:

1. `change_classification`
   Score `change_level` and watch for `L2/L3` boundary mistakes.
2. `reuse_decision`
   Score `reuse_decision` and protect against unsafe auto-reuse.
3. `review_gating`
   Score `review_decision`, `human_review_required`, and escalation reason coverage.

Maintain and grow examples for:

- short ambiguous labels such as `Open`, `Continue`, `Photos`
- fuzzy reuse versus new-key decisions
- pricing, legal, and identity examples
- placeholder-heavy strings
- strict-length toasts and buttons

Prefer raw artifacts plus expected classifications over prose-only test cases.

## Success Criteria

Following Anthropic's recommendation, keep success criteria specific and measurable. The shipped eval pack uses these initial thresholds:

- `change_level_accuracy >= 0.90`
- `l2_l3_recall >= 0.95`
- `high_risk_l3_false_negatives == 0`
- `reuse_auto_precision >= 0.98`
- `review_human_gate_recall == 1.00`
- `review_pass_precision >= 0.95`

These are starting thresholds, not immutable targets. Tighten them only after you have enough real examples.

## How To Run

1. Export the eval pack to CSV when you want to use Claude Console Evaluate:

   `python3 scripts/export_model_eval_csv.py assets/model-eval-pack.json --output /tmp/i18n-model-evals.csv`

2. Run your prompt or agent workflow and collect structured predictions with this contract:

   - `case_id`
   - `change_level`
   - `reuse_decision`
   - `review_decision`
   - `human_review_required`
   - `must_ask_for_context`
   - `reason_codes`

3. Score the predictions:

   `python3 scripts/score_model_evals.py assets/model-eval-pack.json predictions.json --report /tmp/i18n-model-eval-report.json --fail-on-thresholds`

4. Use mismatch slices, not just the headline score, to decide what to improve next.

## Scoring Strategy

Follow Anthropic's grading order:

- use code grading first for exact labels
- use reason-code coverage for partial diagnostics
- use human or LLM grading only when a field cannot be reduced to a stable rubric

For this skill, exact labels should cover most of the regression surface. Human or LLM grading is still useful for:

- coordinator follow-up quality
- translator scenario fit across languages
- reviewer explanation quality

See `references/eval-rubrics.md` for the normalized output contract and reason-code legend.

## Real-World Case Intake

Do not wait for a large retrospective to improve the eval pack. When a user or partner team finds a real mistake:

1. collect the example through the team's normal workflow such as issue tracking, PR review, chat, or a shared sheet
2. reduce it to a reproducible case with normalized inputs and expected labels
3. curate it before promoting it into the gold eval pack

Keep the eval pack focused on repeatable business failures such as wrong reuse decisions, missed human gates, placeholder breakage, or scene mismatches. Map user-visible problems into internal labels only during curation.
