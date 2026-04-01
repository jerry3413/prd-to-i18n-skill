# Coordinator Examples

Use these only when the current request matches the same branch. The core rules live in [coordinator-core.md](coordinator-core.md).

## Example 1: Ambiguous PRD Translation

User request:

```text
翻译我的 PRD
```

Good follow-up:

```text
你是要我翻译整个 PRD，还是只把里面会出现在产品里的文案整理出来做多语言？
这两个流程不一样。我先不默认。
```

## Example 2: Explicit Delivery Intent

User request:

```text
文案做多语言交付
```

Good follow-up:

```text
好，我按交付包来做。

还差这些信息我才能继续：
1. 这次哪些内容算进交付范围；如果 PRD 混了多个端或多个系统，把范围说清楚
2. 要哪些语言
3. 这块以前有没有旧 key、旧翻译、旧交付包，或者可查询的导出/API；没有就直接说没有
4. 你们团队最后拿到的交付长什么样；如果只说 JSON / CSV / XLSX，我还需要知道字段结构

如果你们有固定模板或旧样本，也一起发我。
```

## Example 3: Carrier Only Is Not Enough

User request:

```text
英文、法语、德语、意大利语
安卓、iOS、以及 APP 里后端返回给用户的文案
输出 json
```

Good follow-up:

```text
语言和范围我收到了，但我还不能直接按 JSON 开始。

还差两点：
1. 这块以前有没有旧包、旧翻译或可导出的历史数据；没有直接说没有
2. 你要的 JSON 具体是什么结构；运行时语言包、翻译交付表，还是你们内部固定 schema

如果有旧样本，直接发我一份。
```

## Example 4: Ambiguous Short Label

User request:

```text
Please translate this key. app_identify_psy_photos = Photos
```

Good follow-up:

```text
`Photos` 这个词上下文不够，可能是 tab、按钮、来源选择或相册标题。
请补 `screen`、`component` 和一句背景，或者直接发截图。
如果你现在没有，我也可以先给草案，但我会标成 review-required。
```

## Weak Patterns

Avoid replies like:

- `Can you provide more information?`
- `I will extract everything first and confirm later.`
- `Please choose between basic, review, and strict mode.`
- `我先按默认 manifest + CSV + iOS + Android 出一版，你再确认。`
