---
name: beex-release-all
description: Orchestrate a gated full BeeX release across H5, iOS, Android, business services, admin service, SSO, AI Ops Worker, admin web, docs, and official site. Use whenever the user asks for a full release, all services deployment, end-to-end release, test-to-production promotion, or coordinated app and backend publication.
---

# Release All BeeX Components

Use the bundled deterministic command:

```bash
beex-release inventory
beex-release --help
```

Read `references/release-matrix.md` before changing release ownership or pipeline IDs. Read `references/full-release-runbook.md` for coordinated production releases.

## Release model

Split a full release into three explicit phases. Do not run everything blindly in one irreversible operation.

### 1. Deploy test

```bash
beex-release all --phase test
```

This builds an H5 `DRAFT` and deploys test backend/admin components. Complete scenario QA and record the exact H5 package and business-service commit.

### 2. Promote production

```bash
beex-release all --phase prod \
  --service-commit <tested-service-sha> \
  --admin-service-commit <tested-admin-service-sha> \
  --h5-version <tested-h5-version>
```

The command deploys services. H5 remains an audited BeeX Admin action: transfer the exact tested package, gray-release it, then publish it.

### 3. Build native apps

```bash
beex-release all --phase native \
  --target prod \
  --backend-env id-prod \
  --version <version> \
  --build <build> \
  --h5-version <published-h5-version>
```

This uploads iOS to App Store Connect and builds an Android AAB.

SSO and AI Worker have independent shared-service lifecycles. Add `--include-shared` only when those repositories are intentionally part of the release.

## Mandatory behavior

- Start with `--dry-run` for a new environment or changed pipeline topology.
- Stop on the first failed gate, pipeline, build, or health check.
- Never expose credentials in output or release records.
- Report every released component with environment, Git SHA, artifact/version, pipeline result, and verification.
- Write release records under `<workspace>/.beex-release-records/`.
- Use component Skills for one-off releases instead of invoking the full train.
