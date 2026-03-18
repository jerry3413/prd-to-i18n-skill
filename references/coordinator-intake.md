# Coordinator Intake

## Purpose

Use the coordinator protocol as the front door to the skill. The coordinator should usually be the main conversation rather than a subagent. Its job is to help the user succeed with minimal friction:

- classify the request
- assess readiness
- ask only the smallest set of blocking questions
- explain what can proceed now and what will be downgraded
- route work to translator and reviewer only after the manifest slice is ready

In user-facing conversation, keep the language plain. Infer internal modes and policies yourself instead of asking the user to choose between `basic`, `review`, `strict`, `inherit`, `template`, or `canonical` unless they explicitly ask.
Treat `draft-only` and `release-ready` as internal terms. When talking to users, ask instead whether they want a simple draft copy list or a final package the team can use directly.

## Why This Role Stays In The Foreground

Anthropic's latest guidance favors keeping clarification-heavy work in the main conversation while pushing self-contained tasks to subagents. Intake belongs in the main flow because user clarification is often the real bottleneck, background workers do poorly when they must stop to ask questions, and Claude Code subagents cannot spawn additional subagents.

## Intake Algorithm

1. Classify the request.
   Choose one:
   - `new-build`
   - `change-sync`
   - `dedupe`
   - `translation-fix`
   - `export-only`
2. Inventory the inputs already present.
   Track:
   - PRD
   - PDF attachments
   - screenshots or Figma export
   - whether the request is `draft-only` or `delivery-intent`
   - runtime capability path: `text-first`, `native-vision`, `vision-extension`, `local-ocr`, or `manual-fallback`
   - localization snapshot or API result
   - context sidecar
   - glossary or brand rules
   - target output formats
   - owners for high-risk copy
3. Decide readiness.
   Mark each missing item as either:
   - `blocking`
   - `non-blocking but quality-reducing`
4. Ask questions only for blocking items.
   Ask at most 3 questions in one round.
   Prioritize the highest-leverage missing item first.
   Before expensive extraction from a raw PDF, Word file, or mixed PRD bundle, allow only lightweight preflight checks such as file type, page count, and whether text appears selectable.
5. State the fallback mode.
   If a non-blocking item is missing, continue and say what mode the skill will use instead.
6. Freeze the manifest slice before delegation.
   Do not send work to translator or reviewer until the slice no longer needs user clarification.

## Foolproof Defaults

Prefer the simplest interpretation first:

- if the user gives a PRD or copy list, start from `new-build` or `change-sync`
- if the user gives a key and one string, start from `translation-fix`
- if the user gives a manifest or only asks for output files, start from `export-only`
- if the user gives a folder of exported resources, accept the folder directly instead of asking them to enumerate file descriptors
- if the user gives a PRD, PDF, Word spec, or release document, do not jump straight into translation or full-text extraction; first confirm in plain language whether they want a draft copy table or a final developer-ready package
- after the user confirms the final delivery path, ask for the current localization baseline and the target outputs

When asking for data, prefer:

- one export folder over many explicit file specs
- one context sidecar over repeated per-string explanations
- one blocking question over a checklist

Before processing multimodal evidence, run the capability route. See [Capability Routing](capability-routing.md).
Use [Decision Tables](decision-tables.md) for source priority, fallback behavior, and human-gate triggers.

When Claude Code project subagents are available, the main thread should still own orchestration. If you use the optional `i18n-coordinator` helper template from `assets/helper-agents/`, use it only to draft a readiness summary, then return to the main thread before dispatching translators or reviewers.

## What Counts As Blocking

- no source text or PRD for a `new-build`
- no confirmed goal yet when the request starts from raw PRD/PDF/Word materials and it is still unclear whether the user wants a draft copy table or a final delivery package
- no current snapshot when the user asks for dedupe, reuse, or change sync
- no current snapshot when the request is clearly release prep or handoff work and the user has not opted into draft-only mode
- no business context for ambiguous or high-risk copy
- no reliable text extraction for image-only or scanned high-risk content
- no target output format when the user explicitly asks for delivery bundles
- no target output format or handoff standard when the request is clearly release prep, handoff, import, or team delivery
- no owner when high-risk content must route to human approval

PRD is not blocking for `translation-fix`, `dedupe`, or `export-only`.

## What Usually Does Not Block

- missing screenshots for low-risk copy when the PRD and context are already clear
- missing glossary for generic UI labels
- missing sidecar when the user only wants basic mode normalization or export

## Question Design Rules

Every question should include:

- `why`
- `accepted_formats`
- `fallback`

Prefer file or field requests over open-ended prompts. Instead of asking for “more context,” ask for `screen`, `component`, and `background`.

Good:

- “Before I spend time pulling text out of this document, do you want me to first整理一版待翻译文案, or do you want a final multi-language package your team can use directly? If you want the final package, please also send the current localization export and tell me the final output format.”
- “Please provide a folder that contains iOS `.strings`, Android `strings.xml`, JSON locale files, or CSV exports so I can run dedupe and reuse checks.”
- “Please tell me what final handoff you need: iOS `.strings`, Android `strings.xml`, Web/App JSON, CSV, manifest only, or a custom import schema. Without that, I can only stop at a draft manifest or CSV.”
- “For `app_identify_psy_photos`, please provide `screen`, `component`, and `background`. Without that, I will mark it `review-required`.”
- “This PDF page appears to be scanned. Please provide a text export or confirm the copied sentence manually for the pricing section.”
- “If your runtime has no built-in vision, tell me whether you have configured an external OCR/vision extension or only local OCR.”

Weak:

- “Can you provide more information?”
- “Tell me more about the context.”
- “Please choose between basic, review, and strict mode.”

## Output Contract

Use XML tags for coordinator-internal summaries. When replying directly to end users, paraphrase the same content in short plain language instead of exposing raw XML unless structured output is explicitly useful.

Internal XML contract:

```xml
<task_mode>new-build</task_mode>
<ready_now>
PRD is present. Screenshots are missing but optional for this batch.
</ready_now>
<known_inputs>
- PRD markdown
- raw PRD input
</known_inputs>
<missing_required>
- Confirm whether the user wants a draft copy list or a final delivery package
</missing_required>
<questions>
  <question id="goal">
    <why>I need to know whether you want a simple draft list of translatable copy, or a final package your team can import or hand to developers.</why>
    <accepted_formats>Reply with either “draft copy list” or “final delivery package”. If you want the final package, also include the current export folder and the target outputs you need.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before heavy extraction and will not pretend I can finish final delivery.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will either continue with draft extraction or ask for the baseline and output target needed for final delivery.
</next_step>
```

## Prompt Structuring Rules

Follow Anthropic's latest prompting guidance:

- use clear role instructions
- use XML tags consistently
- place long PRDs and large data blobs near the top when prompts are long
- include 3 to 5 examples for recurring formats
- keep questions specific and answerable
- if the source came from images or scanned PDFs, state the confidence limit explicitly

## Few-Shot Examples

### Example 1

User request:

```text
Here is the PRD. Please prepare i18n for the next release.
```

Coordinator response:

```xml
<task_mode>new-build</task_mode>
<ready_now>
I can start from this PRD, but I should confirm the target outcome before doing the heavier extraction work.
</ready_now>
<known_inputs>
- PRD markdown
- raw PRD input
</known_inputs>
<missing_required>
- Confirm whether the user wants a draft copy list or a final delivery package
</missing_required>
<questions>
  <question id="goal">
    <why>I need to know whether you want me to first整理一版待翻译文案, or whether you want a final package your team can use directly. The final package path also needs the current catalog and the handoff format.</why>
    <accepted_formats>Reply with either “draft copy list” or “final delivery package”. If you want the final package, also send an export folder / iOS .strings / Android strings.xml / CSV / JSON and the target outputs you need.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before the heavier extraction steps instead of pretending I can finish the final delivery flow.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will either continue with draft extraction or ask for the baseline and output target needed for final delivery.
</next_step>
```

### Example 2

User request:

```text
I exported iOS and Android strings. Please update changed copy from this new PRD and ship Android, iOS, and Web JSON.
```

Coordinator response:

```xml
<task_mode>change-sync</task_mode>
<ready_now>
I have enough to begin normalization and diffing.
</ready_now>
<known_inputs>
- PRD markdown
- iOS strings
- Android strings
- target outputs: Android, iOS, Web JSON
</known_inputs>
<missing_required>
- None
</missing_required>
<questions></questions>
<next_step>
I will normalize the snapshot, classify copy changes into L0-L3, then build the manifest and execution plan.
</next_step>
```

### Example 3

User request:

```text
Please translate this key. app_identify_psy_photos = Photos
```

Coordinator response:

```xml
<task_mode>translation-fix</task_mode>
<ready_now>
I have the key and source text, but not enough context to trust a final translation.
</ready_now>
<known_inputs>
- key
- source text
</known_inputs>
<missing_required>
- scene context for this label
</missing_required>
<questions>
  <question id="context">
    <why>The word “Photos” can mean a tab, a button, a picker source, or a gallery label.</why>
    <accepted_formats>Provide `screen`, `component`, and one sentence of background, or attach a screenshot.</accepted_formats>
    <fallback>If you do not have that yet, I can still draft translations but will mark them `review-required`.</fallback>
  </question>
</questions>
<next_step>
After I receive the context, I will decide whether this stays in basic mode or can move into review mode.
</next_step>
```

### Example 4

User request:

```text
I only have a screenshot and a PDF export. Can you still help me prepare i18n?
```

Coordinator response:

```xml
<task_mode>new-build</task_mode>
<ready_now>
I can help from the screenshot and PDF, but I should confirm the target outcome before I spend time extracting text from them.
</ready_now>
<known_inputs>
- screenshot evidence
- PDF evidence
</known_inputs>
<missing_required>
- Confirm whether the user wants a draft copy list or a final delivery package
</missing_required>
<questions>
  <question id="goal">
    <why>I need to know whether you want me to first整理出待翻译文案, or whether you want a final package your team can use directly.</why>
    <accepted_formats>Reply with either “draft copy list” or “final delivery package”. If you want the final package, also send the current localization export and the target output format.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before the heavier extraction steps.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will do a light extraction-quality check and then either build a draft copy list or continue toward final delivery.
</next_step>
```
