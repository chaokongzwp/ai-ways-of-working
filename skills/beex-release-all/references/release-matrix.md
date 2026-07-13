# BeeX Release Matrix

This file is the source of truth for repository ownership and deployment entry points.

| Component | Repository | Test release | Production release | Verification |
| --- | --- | --- | --- | --- |
| App H5 | `beex-app-h5` | Yunxiao `4987658`, register `DRAFT` | Transfer the exact tested package in BeeX Admin, then gray/publish | App latest-package API + `h5-id(-test)` |
| iOS | `beex-app` | Local signed build or TestFlight upload, version `88.88.88` | Explicit semantic version/build, upload to App Store Connect | App Store Connect processing + launch test |
| Android | `beex-app` | APK, version `88.88.88` | AAB with explicit version/build | Install test or Play Console upload |
| Business services | `beex-service` | Yunxiao `5109562,5109563,5109564,5109565` | Promote exact tested commit through `5109294,5109295,5109296,5109297` | `/actuator/health` + scenario smoke test |
| Admin service | `beex-admin-service` | Yunxiao `5018487` | Yunxiao `5109432` | `admin-api-*/actuator/health` |
| Admin page | `beex-admin-page` | Yunxiao `5052020` | Same static site pipeline | `https://admin.beexofficial.com/` |
| SSO | `beex-sso` | Shared Yunxiao `5056734` | One shared deployment, no country test/prod split | `sso.beexofficial.com/actuator/health` + login smoke test |
| AI Ops Worker | `ai-ops-worker` | Shared Yunxiao `5122057` | One shared ops deployment, no country test/prod split | Worker `/health`, self-check, and alerts |
| Product docs | `beex-doc` | Controlled OSS/CDN script | Same domain | `https://prd.beexofficial.com/` |
| Official site | `beex-official-site` | Controlled OSS/CDN script | Same domain | `https://www.beexofficial.com/` |

## Non-negotiable gates

1. The repository worktree is clean.
2. Local `HEAD` equals `origin/<branch>` before a release.
3. H5 is built once. Production receives the same tested package, never a rebuild.
4. Business service production receives the exact tested commit through the release pointer branch.
5. Native packages record the bundled H5 version, native version, build number, and Git commit.
6. Native signing target and backend environment are separate inputs; record both.
7. A successful pipeline is not a successful release until health checks and one business smoke test pass.
8. Never print or persist AK/SK, tokens, P8 content, or passwords in release records.

## Environment token aliases

The release scripts accept one of:

- `YUNXIAO_TOKEN`
- `BEEX_YUNXIAO_TOKEN`
- `SEAHUB_YUNXIAO_TOKEN`

App Store Connect upload additionally requires:

- `ASC_API_KEY_ID`
- `ASC_API_ISSUER_ID`
- `ASC_API_KEY_PATH`

Static OSS/CDN releases use the variables documented by each repository's controlled deploy script.
