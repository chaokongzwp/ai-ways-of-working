# AGENTS.md — 给 AI 的工作指令

> 你（AI）正在一个用「**AI 原生工作方式**」运作的项目里。本文是你的**执行约定**，开工前先读完。
> Codex 会自动读本文；Claude Code 读 `CLAUDE.md`（已转发到这里）；其他工具见 README「AI 接入」。
> **为什么要这么干**（先理解动机）：[`guide/why-ai-native.html`](./guide/why-ai-native.html)。
> 完整背景：[`guide/methodology.html`](./guide/methodology.html)（协作方式）· [`guide/doc-playbook.html`](./guide/doc-playbook.html)（怎么写文档）· [`guide/deploy.html`](./guide/deploy.html)（上线/门禁）。

---

## 一句话

**人负责「想清楚」和「判断对错」，你负责「做出来」，文档（`docs/`）是唯一的通信介质。**

---

## 你的工作循环（每个任务都按这个走）

1. **先复述确认**：把人的需求复述一遍，列出边界、盲点、不确定项。**不确定就问，别猜着做。**
2. **出方案让人选**：给 2–3 个方案 + 各自权衡，让人拍板。**别自作主张选大方向。**
3. **执行**：写码 / 改文档 / 部署。
4. **给验证证据**：自测并给出**可复现**的证据（命令、输出、截图、链接），不要只说「done」。
5. **落进文档**：把结果写进 `docs/` 对应文档，并更新 `docs/feature-status.html` 的状态徽章。**没落文档＝没做完。**

---

## 写文档时（本项目最高频的活，务必遵守）

- **形态**：纯静态**单文件 HTML**，放 `docs/`，零构建，`file://` 双击可看；不引入框架/打包/CDN。
- **用模板**：从 `docs/` 现成模板 copy，别从零写——
  `index.html`（导航）· `overview.html`（业务总纲）· `scenario-1-flow.html`（场景流程）· `xxx-design.html`（设计方案）· `feature-status.html`（全盘状态）。
- **配色**：只用每个文件 `:root{ --brand … }` 里的 **token**，不硬编码颜色。换项目只改 token。
- **流程图**：一律用 **Mermaid**（引 `./assets/mermaid.min.js`）。**改图=改文本**，不要贴图片。
- **状态徽章三色**：✅ `st done` 已完成 · 🔵 `st wip` 部分待验 · 🟡 `st todo` 待完成。贯穿全库。
- **可配参数**：每个场景底部留「⚙️ 本场景可配参数」表（参数/初始值/配置位置/状态）——给运营看。
- **铁律框**：开发/测试必看的硬规则放 `.warn` 红框。
- **返回导航**：每页顶部 `← 返回文档导航` 链回 `index.html`。

---

## 铁律（不可违反）

1. **不臆造数值**。不知道的数就标 `〔TODO〕` 或问人，绝不编一个看起来合理的。
2. **单一真值来源**。同一个数值/状态只定义一处，其他文档**指向**它，不复制粘贴。
3. **总纲先行**。新项目先写 `overview.html` 把业务一页讲清，再铺场景，**不要上来建一堆空壳**。
4. **无黑话**。术语要让业务/运营/测试都能看懂；维护并遵守项目的「禁用词表」。
5. **改文档前先看** [`guide/doc-playbook.html`](./guide/doc-playbook.html) 的模板骨架和 §7 可抄代码片段。
6. **每页页脚声明真值来源**（数值/状态以线上 or 某权威设计稿为准）。

---

## 需要时去读

| 你要做的事 | 看这份 |
|---|---|
| 理解怎么和人协作、分工 | [`guide/methodology.html`](./guide/methodology.html) |
| 写/改文档（含 token、Mermaid、可配参数、术语 hover 的可抄代码） | [`guide/doc-playbook.html`](./guide/doc-playbook.html) |
| 把文档站上线、加飞书登录门禁、配变更通知 | [`guide/deploy.html`](./guide/deploy.html) |

---

**记住**：你出方案、人拍板；你执行、人验收；结果一律落进 `docs/`。无黑话 · 一页读懂先行 · 单一真值来源 · 三色徽章 · 图即文本。
