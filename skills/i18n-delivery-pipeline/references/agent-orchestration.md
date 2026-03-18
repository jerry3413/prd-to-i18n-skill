# Agent Orchestration

## Why This Workflow Uses Two Worker Agents

Use one agent to generate translations and a second agent to review them. This follows an evaluator-optimizer loop:

1. translator produces a draft
2. reviewer scores it against explicit criteria
3. failed slices go back for revision
4. only passing slices proceed to deterministic QA and bundle export

Do not collapse these roles into one prompt unless the batch is tiny and low-risk.

## Default Scheduling Policy

Use the main coordinator for shared-context stages:

- PRD reading
- screenshot interpretation
- manifest skeleton creation
- key reuse versus new-key decisions
- risk and change classification
- final release synthesis

Use subagents for self-contained stages that return summaries:

- translation generation for prepared manifest slices
- review and gating for prepared manifest slices
- snapshot preprocessing or verbose QA runs when you want to keep noisy output out of the main context

## When To Stay Serial

Keep the pipeline serial when:

- later work depends on exact earlier output
- a human or owner must review before moving on
- the slice is high-risk
- the slice is ambiguous or missing context
- placeholders or strict length budgets need careful preservation
- the model may need clarification rather than blind continuation

Examples:

- `L2` and `L3` copy changes
- pricing, payment, legal, or identity-verification strings
- any batch where the English source is still unstable

## When To Run In Parallel

Parallelize only after the coordinator freezes the manifest slice and only when slices are independent.

Good parallel batches:

- low-risk or medium-risk copy
- `L0` or `L1` changes
- complete `screen + component + intent + background`
- no ambiguous placeholders
- no strict character budget

Preferred grouping:

- first by `screen`
- then by risk level
- then by locale set if locale coverage differs

Default batch limits:

- `max_entries_per_slice = 50`
- `revision_loop_limit = 2`

If a safe slice grows beyond the limit, split it before dispatch.

## When To Use Background Workers

Run workers in the background only when they should not ask questions mid-task:

- translation of low-risk slices with complete context
- export generation
- large QA runs with pre-approved tool access

Keep workers in the foreground when they may need clarification or approval:

- review of high-risk slices
- any batch with unresolved placeholder or glossary conflicts
- any batch that may escalate to a human checkpoint

## When Not To Use Agent Teams

Do not use agent teams by default. Anthropic recommends subagents for focused tasks where only the result matters, and reserves agent teams for cases where workers need to communicate directly.

This localization workflow rarely needs direct worker-to-worker debate because:

- the coordinator owns policy
- translator and reviewer operate on prepared slices
- results are easier to audit when they flow back through one coordinator

Use agent teams only for very large launches where multiple surfaces, owners, or repositories need concurrent discussion and independent context over a long span.

## Revision Loop

For every failed review:

1. keep the failing slice isolated
2. send only the reviewer findings back to the translator
3. regenerate only the failed locales or entries
4. rerun review on that slice
5. stop after `revision_loop_limit`, then escalate to a human

## Tooling Guidance

Keep agent interfaces simple and hard to misuse:

- feed workers canonical manifest slices, not ad hoc prose
- prefer stable field names over free-form instructions
- preserve absolute paths in tool calls and artifact references
- log intermediate plans when you need auditability

Run `scripts/plan_execution.py` before dispatching work so the policy becomes a concrete plan rather than an implicit habit.
