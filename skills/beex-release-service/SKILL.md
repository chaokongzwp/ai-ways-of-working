---
name: beex-release-service
description: Deploy and verify BeeX backend components through their Yunxiao pipelines, including business services, admin service, SSO, and AI Ops Worker. Use whenever the user asks to deploy a service, promote a tested commit to production, inspect a backend release, or release all server-side components.
---

# Release BeeX Services

Supported country services: `business` and `admin-service`.

Supported shared services: `sso` and `ai-worker`. They have one fixed deployment target and are not duplicated as `id-test` / `id-prod`.

## Test release

```bash
beex-release preflight <component> --check-origin
beex-release service <component> --env id-test --comment "<summary>"
```

## Production release

For the business service, always promote the exact tested commit:

```bash
beex-release service business --env id-prod --commit <tested-sha>
beex-release service admin-service --env id-prod --commit <tested-sha>
```

For a shared service, release it only when that repository changed:

```bash
beex-release service sso --env shared
beex-release service ai-worker --env shared
```

## Verification

1. Wait for every split pipeline to finish.
2. Check the component health endpoint.
3. Run one scenario-level smoke test for the changed behavior.
4. Report component, environment, commit, pipeline/run ID, health result, and residual risk.

## Guardrails

- Commit and push before triggering a pipeline.
- Production must not deploy an untested local HEAD by convenience.
- SSO and AI Worker are shared infrastructure; do not pretend they have separate country test/prod pipelines.
- The business production script moves `release/<env>` to exactly the supplied commit using `--force-with-lease`.
- Do not SSH-deploy when a component has a Yunxiao pipeline.
- Read `../beex-release-all/references/release-matrix.md` for current pipeline ownership.
