---
name: beex-release-android
description: Build and verify BeeX Android APK or AAB releases, including internal 88.88.88 packages and production packages with a published H5 offline bundle. Use whenever the user asks to compile, package, publish, or provide an Android BeeX build.
---

# Release BeeX Android

Use the repository-owned build and H5 bundling scripts through `beex-release`.

## Internal APK

```bash
beex-release preflight native --check-origin
beex-release android --target test --backend-env id-test \
  --version 88.88.88 --build <unique-build> \
  --expected-h5-version <h5-version> --format apk
```

## Production AAB

```bash
beex-release android \
  --target prod \
  --backend-env id-prod \
  --version <semantic-version> \
  --build <unique-build> \
  --expected-h5-version <published-h5-version> \
  --h5-source remote \
  --format aab
```

## Verification

Report the output path, size, SHA256, version, build number, Git SHA, package name, environment-switch visibility, and bundled H5 version. Install and smoke-test APKs when a device is available.

## Guardrails

- `88.88.88` is an internal test version and may expose the environment switch.
- Production requires explicit version and build values.
- Android build numbers must be numeric and no greater than `2100000000`.
- `--target` controls release packaging; `--backend-env` controls which API/H5 environment is bundled.
- The release stops if the embedded H5 version differs from `--expected-h5-version`.
- Prefer APK for direct QA and AAB for store delivery.
- This skill builds Android artifacts. Do not claim Google Play upload unless Play publishing credentials and an upload workflow are actually configured.
