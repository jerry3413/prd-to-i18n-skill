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
If the user appears to want a full document translation, do not silently reinterpret that as localization delivery. Clarify the goal first.

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
   - `out-of-scope document translation`, when the user appears to want the whole PRD, PDF, or spec translated as a document instead of extracting UI copy for localization
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
   For raw PRD/PDF/Word requests, the first substantive reply must ask what result the user wants before you describe extraction, translation, or output generation.
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
- if the user asks to translate the whole PRD, the whole PDF, or the whole spec, clarify whether they really want document translation or whether they want localization copy extraction
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
- no confirmed scope yet when the request may actually be full-document translation rather than localization delivery
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

- “Do you want the whole document translated, or do you want me to pull out the user-facing copy and turn it into a localization package? Those are two different workflows.”
- “Before I spend time pulling text out of this document, please tell me which result you want: 1. I first整理一版待翻译文案, or 2. I directly prepare a deliverable multi-language package for your team.”
- “If you want the deliverable package, please also tell me three things: which languages you need, whether you already have existing localization files, and which final format you want.”
- “If you already have localization files, send me the folder directly. iOS `.strings`, Android `strings.xml`, JSON, and CSV are all fine.”
- “Please tell me the final format you want, for example CSV, iOS `.strings`, Android `strings.xml`, Web/App JSON, or all of them. Without that, I can only stop at a draft list.”
- “For `app_identify_psy_photos`, please provide `screen`, `component`, and `background`. Without that, I will mark it `review-required`.”
- “This PDF page appears to be scanned. Please provide a text export or confirm the copied sentence manually for the pricing section.”
- “If your runtime has no built-in vision, tell me whether you have configured an external OCR/vision extension or only local OCR.”

Weak:

- “Can you provide more information?”
- “I’ll extract the PDF and start translating it now.”
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
    <why>I need to know whether you want a draft list of translatable copy first, or a final multi-language package your team can use directly.</why>
    <accepted_formats>Reply with either “draft copy list” or “deliverable package”. If you want the deliverable package, also include the languages you need, any existing localization files, and the final format you want.</accepted_formats>
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

### Example 0

User request:

```text
Please translate this PRD PDF into English.
```

Coordinator response:

```xml
<task_mode>out-of-scope document translation</task_mode>
<ready_now>
I can help, but I first need to confirm whether you want the whole document translated or whether you want the user-facing copy extracted for localization work.
</ready_now>
<known_inputs>
- raw PDF input
</known_inputs>
<missing_required>
- Confirm whether the task is full document translation or localization copy extraction
</missing_required>
<questions>
  <question id="scope">
    <why>Full document translation and localization delivery are different workflows. If I guess wrong, I will do the wrong kind of work.</why>
    <accepted_formats>Reply with either “translate the whole document” or “extract the user-facing copy for localization”.</accepted_formats>
    <fallback>If you do not decide yet, I will stop after basic file preflight and will not start extraction or output generation.</fallback>
  </question>
</questions>
<next_step>
After you confirm the scope, I will either leave this skill path or continue with the localization workflow.
</next_step>
```

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
    <why>I need to know whether you want me to first整理一版待翻译文案, or whether you want a final package your team can use directly. The final package path also needs your existing localization files, the languages you need, and the final format.</why>
    <accepted_formats>Reply with either “draft copy list” or “deliverable package”. If you want the deliverable package, also send the languages you need, any existing iOS / Android / JSON / CSV localization files, and the final format you want.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before the heavier extraction steps instead of pretending I can finish the final delivery flow.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will either continue with draft extraction or ask for the baseline and output target needed for final delivery.
</next_step>
```

### Example 1A

User request:

```text
文案做多语言交付
```

Coordinator response:

```xml
<task_mode>new-build</task_mode>
<ready_now>
I can continue with the localization-delivery path.
</ready_now>
<known_inputs>
- raw PRD or PDF input
- goal confirmed: localization delivery
</known_inputs>
<missing_required>
- target languages
- existing localization files
- final output format
</missing_required>
<questions>
  <question id="delivery_inputs">
    <why>These three items decide whether I can dedupe safely and what final package I should generate.</why>
    <accepted_formats>Reply with: 1. the languages you need, 2. whether you already have iOS / Android / JSON / CSV localization files, 3. the final format you want such as CSV, manifest JSON, iOS, Android, Web JSON, or all of them.</accepted_formats>
    <fallback>If you do not have existing localization files yet, say “no existing files” and I will continue in a lower-confidence path for dedupe and reuse.</fallback>
  </question>
</questions>
<next_step>
After I receive those three items, I will continue with extraction and package building.
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
