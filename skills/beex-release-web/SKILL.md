---
name: beex-release-web
description: Publish and verify BeeX web properties, including the admin console, PRD/document site, and official company website. Use whenever the user asks to deploy the admin page, refresh CDN, publish docs, publish the official site, or verify a static web release.
---

# Release BeeX Web Properties

## Admin console

The admin page has a Yunxiao pipeline and must use it:

```bash
beex-release preflight admin-page --check-origin
beex-release web admin-page --comment "<summary>"
```

## Product docs and official site

These repositories currently use controlled OSS/CDN scripts. Direct release is intentionally blocked unless explicitly acknowledged:

```bash
beex-release web docs --allow-direct-static
beex-release web official-site --allow-direct-static
```

Create Yunxiao pipelines for them when releases become frequent; then remove the direct-static exception.

## Verification

- Admin: `https://admin.beexofficial.com/`
- Docs: `https://prd.beexofficial.com/`
- Official site: `https://www.beexofficial.com/`

Check the exact changed page with a cache-busting query. A successful upload is insufficient if CDN still serves an old asset.

## Guardrails

- Never use a local ad hoc OSS command when the repository owns a deploy script.
- Do not deploy demo/archive files not included by the controlled script.
- Preserve privacy, terms, Universal Link, and Android App Link files on the official site.
