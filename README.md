# PRD to I18n Skill

Turn messy PRDs, screenshots, PDFs, and spreadsheets into clean i18n delivery packs.

把 PRD、截图、PDF、表格里散落的文案，整理成能直接交付的多语言包。

This repo contains a reusable AI skill for localization workflows. It is built for teams that need to:

这个仓库里是一套可复用的多语言 workflow skill，适合这些场景：

- extract UI copy from raw product materials
- reuse or generate i18n keys
- translate and review copy with AI
- export ready-to-ship bundles for iOS, Android, Web, and CSV flows

- 从原始产品材料里抽取 UI 文案
- 复用或生成 i18n key
- 用 AI 做翻译和审核
- 导出 iOS、Android、Web、CSV 可直接接入的交付包

## Workflow At A Glance / 流程一览

```mermaid
flowchart LR
    A["Raw inputs / 原始输入<br/>PRD / Word / PDF / XLSX / screenshots"] --> B["Ingest artifacts / 取证归一化<br/>evidence.json"]
    B --> C["Extract copy candidates / 抽取文案候选<br/>copy-candidates.json"]
    C --> D["Build canonical manifest / 构建标准清单<br/>manifest.json"]
    D --> E["Key reuse or new key / 复用或新建 key"]
    E --> F["Translate / 翻译生成"]
    F --> G["Review / 审核把关"]
    G --> H["Deterministic QA / 确定性校验"]
    H --> I["Export bundles / 导出交付包<br/>iOS / Android / Web / CSV"]
```

## What It Handles / 这套 Skill 处理什么

- Raw PRD bundles: Markdown, Word, text-based PDF, XLSX, CSV, JSON
- Visual evidence: screenshots, scanned PDFs, Figma exports
- Existing localization catalogs: iOS `.strings`, Android `strings.xml`, JSON, CSV
- Delivery outputs: manifest JSON, CSV, Web/App JSON, iOS `.strings`, Android `strings.xml`

- 原始 PRD 材料包：Markdown、Word、文本型 PDF、XLSX、CSV、JSON
- 视觉证据：截图、扫描版 PDF、Figma 导出
- 现有多语言资源：iOS `.strings`、Android `strings.xml`、JSON、CSV
- 交付输出：manifest JSON、CSV、Web/App JSON、iOS `.strings`、Android `strings.xml`

## Repo Structure / 仓库结构

```text
.claude/agents/
skills/i18n-delivery-pipeline/
```

- `skills/i18n-delivery-pipeline` is the skill itself
- `.claude/agents` contains the helper agents used by the workflow

- `skills/i18n-delivery-pipeline` 是 skill 本体
- `.claude/agents` 里是 workflow 用到的辅助 agent

## Install Into Another Workspace / 安装到其他工作区

From the target workspace root:

在目标 workspace 根目录执行：

```bash
cp -R /path/to/this-repo/skills .
mkdir -p .claude/agents
cp /path/to/this-repo/.claude/agents/i18n-*.md .claude/agents/
```

Then reopen the workspace or restart your coding agent.

然后重新打开 workspace，或者重启你的 coding agent。

## Quick Start / 快速开始

### 1. Start From Raw Product Materials / 从原始产品材料开始

If you only have a PRD bundle:

如果你手头只有 PRD、Word、PDF、表格、截图这些原始材料：

```bash
python3 skills/i18n-delivery-pipeline/scripts/ingest_artifacts.py ./prd-bundle --output /tmp/evidence.json
python3 skills/i18n-delivery-pipeline/scripts/extract_copy_candidates.py /tmp/evidence.json --output /tmp/copy-candidates.json
python3 skills/i18n-delivery-pipeline/scripts/build_manifest_stub.py /tmp/copy-candidates.json --task-mode new-build --target-locales en,zh-Hans,de --target-outputs manifest,json,ios,android --output /tmp/i18n-manifest.json
```

### 2. Start From Existing Localization Exports / 从现有多语言导出开始

If you already exported current strings:

如果你已经导出了当前多语言资源：

```bash
python3 skills/i18n-delivery-pipeline/scripts/normalize_snapshot.py --input-dir ./exports --metadata ./context.csv --output /tmp/i18n-snapshot.json
python3 skills/i18n-delivery-pipeline/scripts/build_manifest_stub.py /tmp/i18n-snapshot.json --task-mode change-sync --target-locales en,zh-Hans,de --target-outputs manifest,json,ios,android --output /tmp/i18n-manifest.json
```

### 3. Run QA And Export / 跑校验并导出

```bash
python3 skills/i18n-delivery-pipeline/scripts/qa_manifest.py /tmp/i18n-manifest.json --report /tmp/i18n-qa.json
python3 skills/i18n-delivery-pipeline/scripts/emit_delivery_bundle.py /tmp/i18n-manifest.json --out-dir /tmp/delivery-bundle
```

## How It Thinks / 它怎么工作

The workflow stays practical on purpose:

这套 workflow 故意保持“实用优先”：

- structured text beats screenshots
- screenshots help with scene understanding, not source-of-truth text
- short ambiguous labels must ask for context
- high-risk copy stays conservative and human-gated
- exporters adapt one canonical manifest into multiple platform formats

- 结构化文本优先级高于截图
- 截图主要帮助理解场景，不作为默认原文真值
- 短词、歧义词必须补上下文
- 高风险文案保持保守策略，并要求人工把关
- 用一份 canonical manifest 适配多个平台输出

## Validation / 验证方式

Run the built-in smoke checks:

运行内置 smoke check：

```bash
python3 skills/i18n-delivery-pipeline/scripts/run_smoke_evals.py
```

## Good Fit / 适合什么团队

This skill is a good fit if your team has any of these problems:

如果你的团队有下面这些问题，这套 skill 会比较合适：

- product managers create copy in PRDs instead of clean spreadsheets
- translation keys are easy to duplicate and hard to find
- screenshots and design files carry important context
- review quality is inconsistent
- multiple teams need one reusable i18n workflow

- 产品文案散落在 PRD 里，不会先整理成标准表格
- 多语言 key 很容易重复建，也不方便找
- 截图和设计稿里有很多关键上下文
- 翻译审核质量不稳定
- 多个团队都想复用同一套多语言流程
