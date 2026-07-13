---
name: beex-release-h5
description: Build, register, verify, promote, gray-release, publish, or roll back the BeeX App H5 offline package. Use whenever the user asks to publish H5, rebuild the offline package, deploy frontend changes to the app, inspect an H5 release version, or move a tested H5 artifact from test to production.
---

# Release BeeX H5

Use the repository-owned Yunxiao release script through `beex-release`; do not upload H5 files manually.

## Workflow

1. Inspect `beex-app-h5` changes and tests.
2. Commit and push all intended changes. Do not include unrelated work.
3. Run the gate:

   ```bash
   beex-release preflight h5 --check-origin
   ```

4. Build one test artifact and register it as `DRAFT`:

   ```bash
   beex-release h5 --env id-test --comment "<release summary>"
   ```

5. Report the H5 package version and Yunxiao result.
6. Have QA mark that exact package `TEST_PASSED` in BeeX Admin.
7. Transfer that exact package to production, gray-release it, then publish it. Never rebuild production from source.
8. Verify the package returned to a representative app:

   ```bash
   beex-release verify-h5 --env id-prod --expected-version <h5-version>
   ```

## Guardrails

- Normal H5 builds use pipeline `4987658` and register `DRAFT` without refreshing production CDN.
- Do not use the legacy production build pipeline for a normal release.
- Production promotion must preserve package URL, SHA256, entry path, compatibility range, and release notes.
- If a release fails, stop and report the failed gate or pipeline. Do not silently deploy another commit.
- Use BeeX Admin for gray targets and rollback because those actions require an authenticated operator and audit trail.

Read `../beex-release-all/references/release-matrix.md` when pipeline IDs or environment ownership matter.
