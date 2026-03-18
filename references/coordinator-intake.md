# Coordinator Intake

## Purpose

Use the coordinator protocol as the front door to the skill. The coordinator should usually be the main conversation rather than a subagent. Its job is to help the user succeed with minimal friction:

- classify the request
- assess readiness
- ask only the smallest set of blocking questions
- explain what can proceed now and what will be downgraded
- route work to translator and reviewer only after the manifest slice is ready

In user-facing conversation, keep the language plain. Infer internal modes and policies yourself instead of asking the user to choose between `basic`, `review`, `strict`, `inherit`, `template`, or `canonical` unless they explicitly ask.

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

When asking for data, prefer:

- one export folder over many explicit file specs
- one context sidecar over repeated per-string explanations
- one blocking question over a checklist

Before processing multimodal evidence, run the capability route. See [Capability Routing](capability-routing.md).
Use [Decision Tables](decision-tables.md) for source priority, fallback behavior, and human-gate triggers.

When Claude Code project subagents are available, the main thread should still own orchestration. If you use the optional `i18n-coordinator` helper template from `assets/helper-agents/`, use it only to draft a readiness summary, then return to the main thread before dispatching translators or reviewers.

## What Counts As Blocking

- no source text or PRD for a `new-build`
- no current snapshot when the user asks for dedupe, reuse, or change sync
- no business context for ambiguous or high-risk copy
- no reliable text extraction for image-only or scanned high-risk content
- no target output format when the user explicitly asks for delivery bundles
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

- “Please provide a folder that contains iOS `.strings`, Android `strings.xml`, JSON locale files, or CSV exports so I can run dedupe and reuse checks.”
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
- No localization snapshot yet
</known_inputs>
<missing_required>
- Current localization snapshot
</missing_required>
<questions>
  <question id="snapshot">
    <why>I need the current catalog to detect duplicates and recommend key reuse safely.</why>
    <accepted_formats>An export folder, or iOS .strings, Android strings.xml, CSV export, JSON catalog, or API adapter output</accepted_formats>
    <fallback>If you do not have this yet, I can still extract new strings and draft key candidates, but dedupe confidence will be lower.</fallback>
  </question>
</questions>
<next_step>
After I receive the snapshot, I will normalize it and produce a manifest candidate.
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
I can start extracting candidate strings from the PRD now.
</ready_now>
<known_inputs>
- PRD markdown
</known_inputs>
<missing_required>
- Current localization snapshot
</missing_required>
<questions>
  <question id="snapshot">
    <why>I need the existing catalog to detect duplicate keys and reuse opportunities.</why>
    <accepted_formats>An export folder, or iOS .strings, Android strings.xml, CSV, JSON, or API output</accepted_formats>
    <fallback>Without it, I will continue in basic mode and produce new-key suggestions only.</fallback>
  </question>
</questions>
<next_step>
Once the snapshot arrives, I will normalize it and compare it against the extracted strings.
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
I can start from the screenshot and PDF, but the trust level depends on whether the PDF has selectable text and whether the screenshots are legible.
</ready_now>
<known_inputs>
- screenshot evidence
- PDF evidence
</known_inputs>
<missing_required>
- reliable text for any ambiguous or high-risk copy
</missing_required>
<questions>
  <question id="pdf-quality">
    <why>I need to know whether I can extract exact text from the PDF or whether I should treat it as vision-only evidence.</why>
    <accepted_formats>Provide the original PDF, confirm whether the text is selectable, or paste the relevant text manually.</accepted_formats>
    <fallback>If the PDF is image-only, I can still build draft entries from visible text, but ambiguous items will stay review-required.</fallback>
  </question>
  <question id="context">
    <why>For screenshot-derived text, I need enough scene context to avoid mistranslating short labels.</why>
    <accepted_formats>Provide `screen`, `component`, and one sentence of background for each unclear string, or attach annotated crops.</accepted_formats>
    <fallback>Without that, I will keep those entries in basic mode and will not auto-finalize them.</fallback>
  </question>
</questions>
<next_step>
Once I know the extraction quality and have minimal context for unclear labels, I will build the first manifest draft.
</next_step>
```
