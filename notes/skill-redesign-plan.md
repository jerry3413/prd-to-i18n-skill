# Skill 重构方案评审稿

这个文件是评审材料，不是 runtime skill 文档，不参与 skill 的按需加载。

## 实施状态

已执行的改动：

1. 重写 `SKILL.md`
2. 拆分 `references/coordinator-intake.md` 为 `references/coordinator-core.md` 和 `references/coordinator-examples.md`
3. 收缩 `references/input-contract.md`，移除越权的 intake / delivery 语义

本次实施不是把 `SKILL.md` 缩成纯目录，而是保留了两类运行时稳定器：

- `Critical Guardrails`
- `Minimal Decision Anchors`

同时增加了 `Runtime State Map`，用于降低 reference 访问路径不明确带来的执行偏移。

## 目标

这次重构只解决一个核心问题：

当前 skill 的三级加载边界失真了。`metadata`、`SKILL.md`、`references/` 都在重复承担 intake、routing、policy，导致入口层过重，reference 层重复，维护层内容混入运行层。

重构目标不是单纯缩短字数，而是恢复清晰分层：

1. `metadata` 只负责触发。
2. `SKILL.md` 只负责入口路由和导航。
3. `references/` 只负责单一主题的真源规则。
4. `scripts/` 负责低自由度、可重复、易出错的步骤。

## 执行中的修正

在评审后，这个方案做了两点关键修正：

1. 没有把 `SKILL.md` 做成纯导航页。
   入口层仍然保留最小决策锚点，否则模型可能不主动跳转 reference，导致 routing 漂移。
2. 没有把 examples 全部后置。
   `coordinator-core.md` 里保留了两个最小行为锚点，其余示例才拆到 `coordinator-examples.md`。

## 现状判断

### 当前结构问题

1. `SKILL.md` 不是导航层，而是“大一统说明书”。
2. `references/coordinator-intake.md` 已经膨胀成第二个 `SKILL.md`。
3. 同一条规则同时散落在 `SKILL.md`、`coordinator-intake.md`、`decision-tables.md`、`input-contract.md`。
4. `evaluation.md`、`eval-rubrics.md` 这类维护文档暴露在 runtime skill 的主导航里。
5. `SKILL.md` 末尾通过 “Read The References” 一次性列全量 reference，违背渐进式披露。

### 根因

不是“写多了”，而是职责没有切开：

- 触发层写成了能力全景图
- 入口层写成了执行手册
- reference 层写成了重复入口
- 维护层写成了运行层

## 设计原则

### 原则 1：入口层只保留最小运行时信息

`SKILL.md` 只保留这些最小运行时信息：

1. 什么时候用这个 skill
2. 第一问应该问什么
3. 哪些护栏绝不能越过
4. 当前状态该去读哪个 reference
5. 当前输入该调用哪个脚本

凡是超过这五类信息的内容，默认不应该留在 `SKILL.md`。

### 原则 2：一条规则只能有一个真源

例如：

- PRD 翻译分流规则，只能存在于 `decision-tables.md`
- 输入包规范，只能存在于 `input-contract.md`
- manifest 字段规范，只能存在于 `manifest-schema.md`
- human-gate 与 review 规则，只能存在于 `review-policy.md`

不允许继续在多个文件里并行解释同一条规则。

### 原则 3：维护文档和运行文档彻底分离

`evaluation.md`、`eval-rubrics.md`、未来的测试策略、回归说明，都属于维护层，不属于 runtime 路由层。

这部分可以保留在仓库里，但不能继续从 `SKILL.md` 主导航直接暴露。

## 目标结构

```text
SKILL.md
agents/openai.yaml
scripts/
references/
  coordinator-core.md
  coordinator-examples.md
  decision-tables.md
  input-contract.md
  capability-routing.md
  artifact-ingestion.md
  copy-extraction-rules.md
  manifest-schema.md
  review-policy.md
  agent-orchestration.md
notes/
  skill-redesign-plan.md
```

## 文件级修改清单

| 文件 | 现状问题 | 修改内容 | 修改原因 | 修改后的好处 |
| --- | --- | --- | --- | --- |
| `SKILL.md` | 同时承载入口、流程、规则、并发、维护说明 | 重写为精简 front-door 文档，保留 `Use When`、`First Decision`、`Critical Guardrails`、`Runtime State Map`、`Minimal Decision Anchors`、`Artifact Flow` | 入口层现在负担过重，模型一触发 skill 就被迫加载过多流程细节 | skill 触发后更快进入正确分支，减少上下文浪费，同时保留必要的行为锚点避免 routing 漂移 |
| `SKILL.md` frontmatter | `description` 过长，混入能力细节 | 改成一句短触发描述 | metadata 是始终加载层，不应该承载完整流程 | 降低常驻 token 成本，提升触发精度 |
| `references/coordinator-intake.md` | 517 行，已成为第二个入口文件 | 拆成 `coordinator-core.md` 和 `coordinator-examples.md` | algorithm、规则、few-shot 混在一起，导致加载成本过高 | 默认只读核心规则，示例按需再读 |
| `references/coordinator-core.md` | 新文件 | 只保留 intake algorithm、blocking rules、question contract | 这部分是高频运行逻辑，但不需要 few-shot 常驻 | 保持核心流程清晰，便于维护和复用 |
| `references/coordinator-examples.md` | 新文件 | 承接 few-shot、XML 输出样例、提问示例 | 示例有价值，但不应该和核心算法绑死一起加载 | 保留风格约束，同时把上下文成本后置 |
| `references/decision-tables.md` | 结构正确，但部分规则被其他文件重复解释 | 保留为 routing/fallback 真源，并删除其他文件中的重复内容 | 当前最适合承接“如果...则...”规则 | 决策逻辑集中，后续修改不会四处同步 |
| `references/input-contract.md` | 混入 final delivery intake 问题 | 收缩为输入包类型、字段要求、sidecar 规则 | 这个文件应该回答“输入长什么样”，而不是“先问用户什么” | 输入规范清晰，不再和 coordinator 规则冲突 |
| `references/manifest-schema.md` | 单一职责较清晰 | 保持基本不动 | 这是当前较干净的 schema 真源 | 不引入额外重构成本，保留稳定面 |
| `references/review-policy.md` | 与 `SKILL.md` 的 `Apply The Policy` 有重复 | 保留为 review/human-gate 真源，并删除 `SKILL.md` 重复解释 | review 规则应该集中维护 | 风险控制逻辑更稳定，不会入口层和 policy 层双写 |
| `references/agent-orchestration.md` | 与 `SKILL.md` 并发章节重复 | 保留为并发与切片策略真源 | 并发策略是后置知识，不是入口层内容 | skill 初始加载更轻，且并发规则不再散落 |
| `references/evaluation.md` | 维护文档暴露在 runtime 导航 | 从 `SKILL.md` 主导航移除 | eval 属于维护态，不属于用户任务执行态 | 降低 skill 主路径噪音，减少模型误加载 |
| `references/eval-rubrics.md` | 同上 | 从 `SKILL.md` 主导航移除 | rubric 不参与用户任务执行 | 保留维护价值，不干扰运行路径 |
| `README.md` | 与 skill 文档存在解释重叠 | 保留安装、quick start、仓库结构；不再承担 policy 解释 | README 是 repo 入口，不是 skill 入口 | repo 说明和 runtime 指令分工清楚 |

## `SKILL.md` 的具体改写方案

### 保留内容

保留为精简版的只有四段：

1. `Use When`
2. `First Decision`
3. `Scenario Routing`
4. `Artifact Flow`

### 删除内容

以下章节不应继续存在于 `SKILL.md`：

- `Keep It Foolproof`
- `Run The Workflow` 的大部分细节
- `Apply The Policy`
- `Use Large-Batch Tactics`
- `Schedule Work Intelligently`
- `Read The References`
- `Use The Scripts`

### 删除原因

这些内容的问题不是“写错了”，而是“写在了错误的加载层”：

- 有的是 routing rule，应该去 `decision-tables.md`
- 有的是 intake 规则，应该去 `coordinator-core.md`
- 有的是 review policy，应该去 `review-policy.md`
- 有的是 orchestration 策略，应该去 `agent-orchestration.md`
- 有的是维护说明，应该退出 runtime 导航

### 改后的好处

1. skill 一触发，模型先看到的是“先问什么”和“去哪里读”，不是整套作业指导书。
2. 新增规则时，只改真源文件，不再同步修改 3 到 4 处重复文本。
3. 后续如果拆 skill，也能直接从 reference 真源复用，不需要再从一个大 `SKILL.md` 里抽丝剥茧。

## `coordinator-intake` 的拆分方案

### 拆分前的问题

当前这个文件同时承担了：

1. coordinator 角色定位
2. intake 算法
3. blocking 判断
4. question design rules
5. output contract
6. prompt structuring
7. 大量 few-shot examples

这会产生两个问题：

1. 只想读 intake 规则时，也被迫加载大量示例
2. 未来改提问样式时，容易误伤核心 blocking 逻辑

### 拆分后结构

`coordinator-core.md` 只保留：

- purpose
- intake algorithm
- what counts as blocking
- what usually does not block
- question contract

`coordinator-examples.md` 只保留：

- good / weak examples
- XML examples
- ambiguous PRD translation example
- final delivery bundled question example

### 拆分后的好处

1. 默认场景只读核心规则，不加载长示例。
2. few-shot 可以独立扩充，不影响 runtime 主规则。
3. coordinator 逻辑和输出风格分离，后续更容易替换风格但不碰业务护栏。

## 规则去重方案

### 需要集中到 `decision-tables.md` 的规则

- ambiguous PRD/spec translation 必须先问 whole-document 还是 localization delivery
- 已明确是 delivery-intent 时跳过 document-vs-localization split
- final delivery contract 未确认前不能默认输出格式
- human-gate 相关 fallback

### 需要从其他文件删掉的重复解释

- `SKILL.md` 中对上述规则的长篇重复说明
- `input-contract.md` 中对 delivery contract 问题的重复说明
- `coordinator-core.md` 中对 fallback 的重复策略说明

### 去重原因

当前最危险的问题不是 token 浪费，而是“同一条规则未来改动时会发生漂移”。一旦四个文件里有一个忘记改，skill 的行为就会变得不确定。

### 去重后的好处

1. 一条规则只有一个维护入口。
2. 评估失败时可以直接定位到规则真源。
3. 后续做 smoke eval 或人工 review 时，定位成本更低。

## 运行层与维护层分离方案

### 需要退出 runtime 主导航的文件

- `references/evaluation.md`
- `references/eval-rubrics.md`

### 原因

这些文件回答的是：

- 这个 skill 怎么评估
- 哪些阈值算通过
- gold label 怎么定义

它们并不回答：

- 当前用户请求该怎么处理
- 下一步该调用什么脚本
- 哪条规则是 runtime 真源

把它们暴露在 `SKILL.md` 主导航，会让模型把“维护 skill”误当成“执行 skill”。

### 修改后的好处

1. runtime skill 的认知面收窄。
2. 模型更少误读到与当前任务无关的评估文档。
3. skill 的执行路径和 skill 的开发路径彻底分离。

## 脚本层的处理原则

现有脚本 CLI 已经足够稳定：

- `scripts/normalize_snapshot.py`
- `scripts/ingest_artifacts.py`
- `scripts/build_manifest_stub.py`
- `scripts/emit_delivery_bundle.py`

因此不再让 `SKILL.md` 重复讲脚本参数细节，只保留“什么时候调用哪个脚本”。

### 原因

脚本属于低自由度能力，天然比长文字说明更可靠。既然 CLI 已经稳定，就应该让脚本承担精确约束，而不是让 `SKILL.md` 重复描述一遍。

### 修改后的好处

1. 降低入口文档长度。
2. 降低文字规则和 CLI 行为不一致的风险。
3. 后续改参数时，只维护脚本帮助信息和少量 reference，不需要同步修改入口层。

## 不采用的方案

### 不采用方案 1：继续在原 `SKILL.md` 上做局部删减

原因：

这只是减字数，不解决职责错位。删完以后重复规则和层级混乱仍然存在。

### 不采用方案 2：拆成多个 skill

原因：

现在最核心的问题是入口层过重，不是 skill 边界已经成熟到适合拆分。过早拆 skill 会把重复规则复制到多个 skill 中，反而更难收敛。

### 不采用方案 3：保留旧文件同时新增新文件，双轨并存

原因：

这属于兼容性补丁方案。短期看安全，长期一定漂移。你已经明确不要补丁式方案，这里就不做双写。

## 执行顺序

1. 重写 `SKILL.md`
2. 拆分 `references/coordinator-intake.md`
3. 清理 `references/input-contract.md` 的越权内容
4. 去掉 `SKILL.md` 对 eval 文档的主导航暴露
5. 做一次重复规则扫描，确保每条规则只有一个真源

## 验收标准

### 结构验收

1. `SKILL.md` 控制在约 120 行以内。
2. `coordinator-core.md` 控制在约 150 行以内。
3. `coordinator-examples.md` 单独承接示例，不进入默认主路径。

### 逻辑验收

1. ambiguous PRD translation 的第一问仍然存在。
2. final delivery contract 未确认前，仍然不能默认 handoff shape。
3. human-gate 规则仍然完整保留。
4. 同一条 runtime 规则不再重复出现在多个文件中。

### 维护验收

1. 修改某条规则时，只需要改一个真源文件。
2. eval 文档不再干扰 runtime skill 的主加载面。
3. 新 agent 只读 `SKILL.md` 就能知道先问什么、接着读哪个 reference、然后调哪个脚本。

## 下一步

如果你认可这份方案，下一步我会按这份评审稿直接开始改文件，先动：

1. `SKILL.md`
2. `references/coordinator-intake.md`
3. `references/input-contract.md`

改完后再给你一版实际 diff 和新的结构说明。
