# CLAUDE.md

本项目的 AI 工作指令统一维护在 **[`AGENTS.md`](./AGENTS.md)** —— 请先完整阅读它再开始任何工作。

速记（细则全在 `AGENTS.md`）：

- **人想清楚 · 你做出来 · 文档（`docs/`）是唯一通信介质**。
- **工作循环**：复述确认 → 出 2–3 方案让人选 → 执行 → 给可复现验证 → 落进 `docs/` + 更新状态徽章。
- **写文档**：纯静态单文件 HTML，从 `docs/` 模板 copy，只用 `--brand` token，流程图用 Mermaid，状态用三色徽章 ✅🔵🟡。
- **铁律**：不臆造数值（不确定就 `〔TODO〕`/问人）· 单一真值来源 · 总纲先行 · 无黑话。

完整方法论：[`guide/methodology.html`](./guide/methodology.html)（协作）· [`guide/doc-playbook.html`](./guide/doc-playbook.html)（写文档）· [`guide/deploy.html`](./guide/deploy.html)（上线/门禁）。
