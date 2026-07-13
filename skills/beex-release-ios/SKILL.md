---
name: beex-release-ios
description: Build, sign, archive, upload, or verify BeeX iOS releases for TestFlight and App Store Connect. Use whenever the user asks for an iOS build, IPA, TestFlight version, App Store Connect upload, production iOS release, or an iOS package containing a specific H5 offline package.
---

# Release BeeX iOS

Delegate to `beex-app/scripts/build_ios.sh`, `update_bundled_h5_package.sh`, and `upload_ios_appstoreconnect.sh` through `beex-release`.

## Internal test build

```bash
beex-release preflight native --check-origin
beex-release ios --target test --backend-env id-test \
  --version 88.88.88 --build <unique-build> \
  --expected-h5-version <h5-version> --upload
```

`88.88.88` is internal only. Use a unique numeric build number for every App Store Connect upload.

## Production build

1. Confirm the production H5 package is published and verify its version.
2. Commit and push `beex-app`.
3. Run:

   ```bash
   beex-release ios \
     --target prod \
     --backend-env id-prod \
     --version <semantic-version> \
     --build <unique-build> \
     --expected-h5-version <published-h5-version> \
     --h5-source remote \
     --upload
   ```

4. Confirm App Store Connect accepted the upload and report processing status, version, build, Git SHA, and bundled H5 version.

## Credentials

Require `ASC_API_KEY_ID`, `ASC_API_ISSUER_ID`, and `ASC_API_KEY_PATH`. Never print their values or commit the P8 file.

## Guardrails

- A production build requires explicit `--version` and `--build`.
- `--target` controls signing/version behavior. `--backend-env` independently selects the API and H5 environment.
- Default to `--h5-source remote` so the app bundles the published package for the selected target.
- The release stops if the H5 package actually embedded in the IPA differs from `--expected-h5-version`.
- Use `--h5-source zip --h5-zip <path>` only for a verified immutable artifact.
- Do not claim submission for App Review; this workflow uploads a build unless the user separately asks to submit it.
