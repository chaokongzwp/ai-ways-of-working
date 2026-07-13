# BeeX Full Release Runbook

## Phase 1: test environment

1. Commit and push every repository in scope.
2. Run `beex-release preflight <components...> --check-origin`.
3. Run `beex-release all --phase test`.
   Add `--include-shared` only when SSO or AI Worker changed.
4. Test login, link conversion, order sync, wallet/commission, WhatsApp, admin writes, and H5 update.
5. Record the tested business-service commit and H5 package version.

## Phase 2: production services

1. Confirm the tested commit has not changed.
2. Run:

   ```bash
   beex-release all --phase prod \
     --service-commit <tested-beex-service-sha> \
     --admin-service-commit <tested-admin-service-sha> \
     --h5-version <tested-h5-version>
   ```

3. In BeeX Admin, transfer the exact H5 artifact from test to production.
4. Configure a small whitelist gray release, verify it, then publish to all users.
5. Confirm production health endpoints and one real low-risk scenario.

## Phase 3: native packages

Build with the production-published H5 package already available:

```bash
beex-release all --phase native \
  --target prod \
  --backend-env id-prod \
  --version 1.0.1 \
  --build 26071301 \
  --h5-version 20260713120000-abcdef0
```

The build number is shared by iOS and Android in this command, so it must be Android-compatible (`1..2100000000`). The iOS step uploads to App Store Connect. The Android step produces an AAB; store upload remains a separate explicit action until a Play publishing credential and review policy are configured.

## Rollback

- H5: use BeeX Admin to roll back to the previous published package.
- Business service: promote the previous known-good commit through `promote-service-commit.sh`.
- Other services: rerun the component pipeline from the previous known-good branch/commit.
- Native: native binaries cannot be remotely rolled back; use H5 rollback or submit a new build.

## Release records

The command writes non-secret JSON records under:

```text
<workspace>/.beex-release-records/
```

Keep these local or ingest them into the future operations console. Do not commit them to product repositories.
