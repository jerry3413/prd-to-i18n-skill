# Coordinator Intake

## Purpose

Use the coordinator protocol as the front door to the skill. The coordinator should usually be the main conversation rather than a subagent. Its job is to help the user succeed with minimal friction:

- classify the request
- assess readiness
- ask only the smallest set of blocking questions
- explain what can proceed now and what will be downgraded
- route the request into document translation or localization delivery
- route work to translator and reviewer only after the manifest slice is ready

In user-facing conversation, keep the language plain. Infer internal modes and policies yourself instead of asking the user to choose between `basic`, `review`, `strict`, `inherit`, `template`, or `canonical` unless they explicitly ask.
Treat `draft-only` and `release-ready` as internal terms. When talking to users, ask instead whether they want a simple draft copy list or a final package the team can use directly.
If the user appears to want a full document translation, do not silently reinterpret that as localization delivery. Clarify the goal first, then continue in the right branch.
Do not use internal workflow phrases such as “定死目标”, “重处理”, “重提取”, or “freeze the contract” in user-facing replies.
Do not describe internal structure checks such as whether the file is “段落+表格+截图说明”. Tell the user only whether you can extract directly or whether you need a short cleanup pass first.

## Why This Role Stays In The Foreground

Anthropic's latest guidance favors keeping clarification-heavy work in the main conversation while pushing self-contained tasks to subagents. Intake belongs in the main flow because user clarification is often the real bottleneck, background workers do poorly when they must stop to ask questions, and Claude Code subagents cannot spawn additional subagents.

## Intake Algorithm

1. Classify the request.
   Choose one:
   - `document-translation`
   - `new-build`
   - `change-sync`
   - `dedupe`
   - `translation-fix`
   - `export-only`
   - `ambiguous prd/spec translation`, when the user says "translate my PRD", "翻译这个 PRD", or a similar request that could mean either whole-document translation or localization delivery
2. Inventory the inputs already present.
   Track:
   - PRD
   - PDF attachments
   - screenshots or Figma export
   - detected product surfaces, such as app, web, seller, backend-admin, or internal-tool
   - which surfaces are included in this delivery
   - whether the request is `document-translation`, `draft-only`, or `delivery-intent`
   - runtime capability path: `text-first`, `native-vision`, `vision-extension`, `local-ocr`, or `manual-fallback`
   - target languages
   - preferred document output shape when document translation is chosen
   - older localization files or export snapshot
   - delivery content type
   - file format or handoff format
   - sample or template for any custom team schema
   - context sidecar
   - glossary or brand rules
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

- if the user says "翻译我的PRD", "translate this PRD", or something similarly ambiguous, first ask whether they want the whole document translated or whether they want the user-facing copy extracted for localization delivery
- do not default that request into whole-document translation just because the wording contains “翻译” or “translate”
- if the user gives a PRD or copy list, start from `new-build` or `change-sync`
- if the user gives a key and one string, start from `translation-fix`
- if the user gives a manifest or only asks for output files, start from `export-only`
- if the user gives a folder of exported resources, accept the folder directly instead of asking them to enumerate file descriptors
- if the user asks to translate the whole PRD, the whole PDF, or the whole spec, keep the request in this skill and route it into document translation unless they switch to localization delivery
- if the user gives a PRD, PDF, Word spec, or release document, do not jump straight into translation or full-text extraction; first confirm in plain language whether they want a draft copy table or a final developer-ready package
- if the user confirms whole-document translation, ask what language they want; only ask about translated Markdown, bilingual output, or another final shape if that choice actually matters
- after the user confirms the final delivery path, ask the minimum user-facing questions needed to freeze scope:
  - which product surfaces this delivery should cover, but only when the source clearly mixes more than one surface
  - what languages do you need
  - did you do this area before, and do you already have old localization files
  - what kind of deliverable do you want: source-copy list, translation table, reviewer handoff, or import-ready package
  - what file format do you need: CSV, JSON, iOS, Android, Web, or something custom
- only ask for a sample or template when the user says the output must match an existing internal system or old import format
- if a draft copy result is small, show it directly in the conversation first and offer a file only if the user wants one

When asking for data, prefer:

- one export folder over many explicit file specs
- one context sidecar over repeated per-string explanations
- one blocking question over a checklist

Before processing multimodal evidence, run the capability route. See [Capability Routing](capability-routing.md).
Use [Decision Tables](decision-tables.md) for source priority, fallback behavior, and human-gate triggers.

When Claude Code project subagents are available, the main thread should still own orchestration. If you use the optional `i18n-coordinator` helper template from `assets/helper-agents/`, use it only to draft a readiness summary, then return to the main thread before dispatching translators or reviewers.

## What Counts As Blocking

- no source text or PRD for a `new-build`
- no confirmed scope yet when the request may be either full-document translation or localization delivery
- no confirmed scope yet when the user says "翻译我的PRD" or another ambiguous spec-translation request; do not ask for the target language until scope is confirmed
- no target language when the user asked for full-document translation
- no confirmed goal yet when the request starts from raw PRD/PDF/Word materials and it is still unclear whether the user wants a draft copy table or a final delivery package
- no confirmed included surfaces yet when the PRD clearly mixes more than one product surface and the user asked for final delivery
- no target languages when the user asked for final delivery
- no delivery content type when the user asked for final delivery
- no file format when the user asked for final delivery
- no current snapshot when the user asks for dedupe, reuse, or change sync
- no business context for ambiguous or high-risk copy
- no reliable text extraction for image-only or scanned high-risk content
- no sample or template when the user explicitly needs the output to match an existing internal schema or import format
- no owner when high-risk content must route to human approval

PRD is not blocking for `translation-fix`, `dedupe`, or `export-only`.

## What Usually Does Not Block

- missing screenshots for low-risk copy when the PRD and context are already clear
- missing glossary for generic UI labels
- missing sidecar when the user only wants basic mode normalization or export
- missing older localization files for a new-build; continue, but be explicit that duplicate-key detection will be lower confidence

## Question Design Rules

Every question should include:

- `why`
- `accepted_formats`
- `fallback`

Prefer file or field requests over open-ended prompts. Instead of asking for “more context,” ask for `screen`, `component`, and `background`.

Good:

- “你是要我翻整篇文档，还是只把里面需要做多语言的界面文案拎出来？这两个流程不一样。”
- “你是想让我翻译整个 PRD，还是只翻译 PRD 里会出现在产品里的文案？”
- “你是要我先整理一版待翻译文案，还是直接给你一份可以交付的多语言包？”
- “如果你要交付包，我还需要 4 个信息：要哪些语言、以前这块有没有做过多语言、有的话发旧文件、你要的是文案清单还是翻译表还是导入包、最后要什么文件格式。”
- “这份 PRD 里混了不止一种内容范围。你这次要覆盖哪些界面？只做用户端会看到的内容，还是也包含商家端、运营后台或其他内部页面？”
- “如果你们以前做过这块多语言，把旧文件发我就行。我会顺手帮你避开重复建 key。没有也可以直接说没有。”
- “你最后要的内容是什么：源文案清单、翻译表、审核表，还是开发可导入包？”
- “你最后要什么文件：CSV、JSON、iOS `.strings`、Android `strings.xml`、Web JSON，还是别的格式？”
- “如果你们系统有固定模板，或者你想跟旧格式保持一致，发我一份旧样本就行。没有的话我先按通用格式出。”
- “这份文件我可以直接提取。”
- “这份文件我需要先整理一下，再帮你提取文案。”
- “这次只有十几条，我先直接列给你看；如果你要，我再帮你整理成文件。”
- “如果你是要翻译整个 PRD，直接告诉我要翻成什么语言就行。没有特别要求的话，我先按原结构给你一版完整译文。”
- “For `app_identify_psy_photos`, please provide `screen`, `component`, and `background`. Without that, I will mark it `review-required`.”
- “This PDF page appears to be scanned. Please provide a text export or confirm the copied sentence manually for the pricing section.”
- “If your runtime has no built-in vision, tell me whether you have configured an external OCR/vision extension or only local OCR.”

Weak:

- “Can you provide more information?”
- “I’ll extract the PDF and start translating it now.”
- “Tell me more about the context.”
- “Please choose between basic, review, and strict mode.”
- “我现在在确认它是不是段落+表格+截图说明。”
- “我先给你写成一个 md 文件。”
- “后台这块我先默认不翻。”

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
    <accepted_formats>Reply with either “整理待翻译文案” or “直接做交付包”. If you want the delivery package, also include the languages you need, what kind of deliverable you want, and the file format you need.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before heavy extraction and will not pretend I can finish final delivery.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will either continue with draft extraction or ask for the delivery details needed for final output.
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
<task_mode>ambiguous prd/spec translation</task_mode>
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
    <accepted_formats>Reply with either “translate the whole PRD” or “translate only the product copy that appears in the app”.</accepted_formats>
    <fallback>If you do not decide yet, I will stop after basic file preflight and will not start extraction or output generation.</fallback>
  </question>
</questions>
<next_step>
After you confirm the scope, I will either continue with document translation or continue with the localization workflow.
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
    <why>I need to know whether you want me to first整理一版待翻译文案, or whether you want a final package your team can use directly. The final package path also needs the languages, the kind of deliverable, and the file format.</why>
    <accepted_formats>Reply with either “先整理待翻译文案” or “直接做交付包”. If you want the delivery package, also send the languages you need, what kind of deliverable you want, and the file format you need.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before the heavier extraction steps instead of pretending I can finish the final delivery flow.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will either continue with draft extraction or ask for the delivery details needed for final output.
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
- older localization files status
- delivery content type
- final output format
</missing_required>
<questions>
  <question id="delivery_inputs">
    <why>I need these details before I can decide what to generate and how close it needs to be to your team's real handoff format.</why>
    <accepted_formats>Reply with: 1. the languages you need, 2. whether you have older localization files for this area, 3. whether you want a source-copy list, translation table, reviewer handoff, or import-ready package, 4. the file format you want such as CSV, JSON, iOS, Android, Web JSON, or all of them, 5. an old sample if your team has a fixed template.</accepted_formats>
    <fallback>If you do not have older files, say “no old files”. If you do not have a fixed template, say “no template, use the default format”. I can continue, but I will not pretend the result matches your internal schema exactly.</fallback>
  </question>
</questions>
<next_step>
After I receive those delivery details, I will continue with extraction and package building.
</next_step>
```

User-facing version of the same follow-up should usually look like this:

```text
好，我按“交付包”来做。

还差 4 个信息，我拿到就继续：
1. 要哪些语言
2. 以前这块有没有做过多语言？有的话把旧文件发我；没有直接说没有
3. 你要的内容是什么：源文案清单、翻译表、审核表，还是开发可导入包
4. 你最后要什么文件：CSV、JSON、iOS、Android、Web，还是别的格式

如果你们系统有固定模板，或者你想跟旧格式保持一致，再发我一份旧样本；没有就先按通用格式出。
```

### Example 1B

User request:

```text
翻译我的PRD
```

Coordinator response:

```xml
<task_mode>ambiguous prd/spec translation</task_mode>
<ready_now>
I can continue, but I first need to know whether you want the whole PRD translated or whether you want only the UI copy prepared for localization work.
</ready_now>
<known_inputs>
- raw PRD or spec input
</known_inputs>
<missing_required>
- Confirm whether the task is document translation or localization delivery
</missing_required>
<questions>
  <question id="scope">
    <why>Those are two different jobs. If I guess wrong, I will do the wrong kind of work.</why>
    <accepted_formats>Reply with either “翻译整个 PRD” or “只翻译 PRD 里涉及到的产品文案”.</accepted_formats>
    <fallback>If you do not decide yet, I will stop after basic file preflight. I will not default to whole-document translation and I will not start heavy extraction.</fallback>
  </question>
</questions>
<next_step>
After you confirm the scope, I will either ask for the target language and give you a full translated version, or continue with the localization-delivery questions.
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
    <accepted_formats>Reply with either “先整理待翻译文案” or “直接做交付包”. If you want the final package, also send the languages you need, what kind of deliverable you want, the file format you need, and any old sample if your team uses a fixed template.</accepted_formats>
    <fallback>If you do not decide yet, I will stop before the heavier extraction steps.</fallback>
  </question>
</questions>
<next_step>
After you confirm the goal, I will do a light extraction-quality check and then either build a draft copy list or continue toward final delivery.
</next_step>
```
