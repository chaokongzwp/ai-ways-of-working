# AI 工作方式

> 「**用 AI 驱动项目** + **用 HTML 文件当 PRD**」的可复制脚手架。
> Copy 整个目录到新项目，改配色 token 和业务词，就能从 0 搭一套文档体系并上线。

## 👉 先打开 [`index.html`](./index.html)

**所有内容都在文档站里**——双击 `index.html`（`file://` 即可，无需起服务），一页读懂：方法论、模板、怎么上手。

> 这套规范 本身就是用它自己的方法论做的（纯静态 HTML、一页读懂、卡片导航）——**打开就是活样板**。
> 所以这里没有一堆 md 让你啃，方法论都做成了 `guide/` 里的 HTML。

## 目录

```
index.html              ★ 主页（先打开这个）
guide/                  方法论（HTML，给人读）
  ├── methodology.html      项目执行方法论（人想清楚·AI做出来·文档是唯一通信介质）
  ├── doc-playbook.html     文档体系方法论（7原则·6层·模板·可抄代码）
  ├── ai-worker-role.html   AI Worker 角色定义（职责·权限·交付标准·标准机器）
  └── deploy.html           上线 + 飞书门禁 + 变更通知（含踩过的坑）
docs/                   文档模板（copy 改即用）
  ├── index / overview / scenario-1-flow / xxx-design / feature-status .html
  └── assets/ (mermaid.min.js + auth-guard.js 门禁)
scripts/                deploy-oss-cdn.sh · refresh-cdn.py · feishu-doc-change-notify.mjs
AGENTS.md               给 AI —— Codex / 通用约定自动读
CLAUDE.md               给 AI —— Claude Code 自动读（转发到 AGENTS.md）
```

## 让团队的 AI 自动按方法论干活

对方 clone 后无需配置：**Codex 自动读 `AGENTS.md`、Claude Code 自动读 `CLAUDE.md`**。第一句直接说：

> 「按 AGENTS.md 的方法论，帮我写 overview 总纲」

换其他工具，加一行转发文件指向 `AGENTS.md`：
- **Cursor** → `.cursor/rules/methodology.mdc`，内容：`See @AGENTS.md`
- **GitHub Copilot** → `.github/copilot-instructions.md`，内容：`Follow the conventions in AGENTS.md.`
- **Windsurf** → `.windsurfrules`，内容：`Follow AGENTS.md.`

## 上线（可选）

```bash
export ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=xxx
export OSS_BUCKET=your-doc-bucket
export CDN_DOMAIN=docs.example.com    # 可选；留空只传 OSS
bash scripts/deploy-oss-cdn.sh
```

只给内部人看？配飞书登录门禁，详见 `guide/deploy.html`。

---

心法：**人想清楚 · AI 做出来 · 文档是唯一通信介质** · 无黑话 · 一页读懂先行 · 单一真值来源 · 三色徽章 · 图即文本。
