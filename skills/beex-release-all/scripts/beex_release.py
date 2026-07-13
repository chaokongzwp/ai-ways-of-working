#!/usr/bin/env python3
"""Guarded BeeX release orchestrator.

This command does not reimplement builds. It validates Git state and delegates to
the release scripts already owned by each BeeX repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_WORKSPACE = Path(os.environ.get("BEEX_WORKSPACE", "/Users/zwp/x")).expanduser()
ORG_ID = os.environ.get("BEEX_YUNXIAO_ORG_ID", "69f064d17c12f71e8ca61158")
YUNXIAO_ENDPOINT = os.environ.get("BEEX_YUNXIAO_ENDPOINT", "https://openapi-rdc.aliyuncs.com")
TOKEN_NAMES = ("YUNXIAO_TOKEN", "BEEX_YUNXIAO_TOKEN", "SEAHUB_YUNXIAO_TOKEN")


@dataclass(frozen=True)
class Component:
    key: str
    repo: str
    kind: str
    test_pipeline: str | None = None
    prod_pipeline: str | None = None
    repo_url: str | None = None
    health_test: str | None = None
    health_prod: str | None = None


COMPONENTS: dict[str, Component] = {
    "h5": Component(
        "h5", "beex-app-h5", "h5", "4987658", None,
        "https://github.com/chaokongzwp/beex-app-h5.git",
        "https://h5-id-test.beexofficial.com/", "https://h5-id.beexofficial.com/",
    ),
    "native": Component("native", "beex-app", "native"),
    "business": Component(
        "business", "beex-service", "service", "5109562,5109563,5109564,5109565",
        "5109294,5109295,5109296,5109297",
        "https://github.com/chaokongzwp/beex-service.git",
        "https://api-id-test.beexofficial.com/actuator/health",
        "https://api-id.beexofficial.com/actuator/health",
    ),
    "admin-service": Component(
        "admin-service", "beex-admin-service", "service", "5018487", "5109432",
        "https://github.com/chaokongzwp/beex-admin-service.git",
        "https://admin-api-id-test.beexofficial.com/actuator/health",
        "https://admin-api-id.beexofficial.com/actuator/health",
    ),
    "sso": Component(
        "sso", "beex-sso", "shared-service", "5056734", None,
        "https://github.com/chaokongzwp/beex-sso.git",
        "https://sso.beexofficial.com/actuator/health",
    ),
    "ai-worker": Component(
        "ai-worker", "ai-ops-worker", "shared-service", "5122057", None,
        "https://github.com/chaokongzwp/ai-ops-worker.git",
        "http://147.139.167.175:7077/health",
    ),
    "admin-page": Component(
        "admin-page", "beex-admin-page", "web", "5052020", "5052020",
        "https://github.com/chaokongzwp/beex-admin-page.git",
        "https://admin.beexofficial.com/", "https://admin.beexofficial.com/",
    ),
    "docs": Component(
        "docs", "beex-doc", "static", repo_url="https://github.com/chaokongzwp/beex-doc.git",
        health_test="https://prd.beexofficial.com/", health_prod="https://prd.beexofficial.com/",
    ),
    "official-site": Component(
        "official-site", "beex-official-site", "static",
        repo_url="https://github.com/chaokongzwp/beex-official-site.git",
        health_test="https://www.beexofficial.com/", health_prod="https://www.beexofficial.com/",
    ),
}


class ReleaseError(RuntimeError):
    pass


def quote_command(command: Iterable[str]) -> str:
    return " ".join(shlex.quote(str(item)) for item in command)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
    capture: bool = False,
) -> str:
    location = f" (cwd={cwd})" if cwd else ""
    print(f"$ {quote_command(command)}{location}", flush=True)
    if dry_run:
        return ""
    merged_env = os.environ.copy()
    if env:
        merged_env.update({key: str(value) for key, value in env.items()})
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if result.returncode:
        detail = ""
        if capture:
            detail = "\n" + (result.stderr or result.stdout or "").strip()
        raise ReleaseError(f"Command failed ({result.returncode}): {quote_command(command)}{detail}")
    return (result.stdout or "").strip() if capture else ""


def repo_path(workspace: Path, component: Component) -> Path:
    path = workspace / component.repo
    if not (path / ".git").is_dir():
        raise ReleaseError(f"Git repository not found: {path}")
    return path


def git(path: Path, *args: str, dry_run: bool = False) -> str:
    return run(["git", *args], cwd=path, dry_run=dry_run, capture=True)


def repo_snapshot(path: Path, *, check_origin: bool, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {"repo": path.name, "branch": "main", "commit": "DRY_RUN", "subject": "dry run"}
    status = git(path, "status", "--porcelain")
    if status:
        raise ReleaseError(f"Refusing release: {path.name} has uncommitted changes")
    branch = git(path, "branch", "--show-current")
    if not branch:
        raise ReleaseError(f"Refusing release: {path.name} is in detached HEAD state")
    commit = git(path, "rev-parse", "HEAD")
    if check_origin:
        git(path, "fetch", "origin", branch, "--quiet")
        remote = git(path, "rev-parse", f"origin/{branch}")
        if commit != remote:
            raise ReleaseError(
                f"Refusing release: {path.name} HEAD {commit[:8]} != origin/{branch} {remote[:8]}. "
                "Commit and push first."
            )
    return {
        "repo": path.name,
        "branch": branch,
        "commit": commit,
        "subject": git(path, "log", "-1", "--pretty=%s"),
    }


def release_snapshot(path: Path, args: argparse.Namespace) -> dict[str, str]:
    expected_commit = getattr(args, "internal_preflight_commit", None)
    if expected_commit:
        if args.dry_run:
            return {"repo": path.name, "branch": "main", "commit": "DRY_RUN", "subject": "dry run"}
        commit = git(path, "rev-parse", "HEAD")
        if commit != expected_commit:
            raise ReleaseError(
                f"Internal release preflight commit changed: expected {expected_commit[:8]}, got {commit[:8]}"
            )
        allowed_generated = {
            "assets/h5/bootstrap/beex-h5.zip",
            "ios/Runner.xcodeproj/project.pbxproj",
        }
        dirty = []
        for line in git(path, "status", "--porcelain").splitlines():
            changed_path = line[3:].split(" -> ")[-1]
            if changed_path not in allowed_generated:
                dirty.append(changed_path)
        if dirty:
            raise ReleaseError(
                "Unexpected changes appeared after native preflight: " + ", ".join(sorted(dirty))
            )
        return {
            "repo": path.name,
            "branch": git(path, "branch", "--show-current"),
            "commit": commit,
            "subject": git(path, "log", "-1", "--pretty=%s"),
        }
    return repo_snapshot(path, check_origin=not args.skip_origin_check, dry_run=args.dry_run)


def token_value(required: bool = True) -> str:
    for name in TOKEN_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if required:
        raise ReleaseError(f"Set one of: {', '.join(TOKEN_NAMES)}")
    return ""


def request_json(method: str, url: str, *, token: str | None = None, body: Any = None) -> Any:
    headers = {"Accept": "application/json"}
    if token:
        headers["x-yunxiao-token"] = token
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise ReleaseError(f"HTTP {exc.code} from {url}: {raw[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise ReleaseError(f"Request failed for {url}: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()


def extract_run_id(payload: Any) -> str:
    if isinstance(payload, (str, int)):
        return str(payload)
    if isinstance(payload, dict):
        value = payload.get("id") or payload.get("pipelineRunId") or payload.get("runId") or payload.get("data")
        if isinstance(value, dict):
            value = value.get("id") or value.get("pipelineRunId") or value.get("runId")
        if value is not None:
            return str(value)
    return ""


def extract_status(payload: Any) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if isinstance(payload, dict):
        return str(payload.get("status") or payload.get("runningStatus") or payload.get("result") or "UNKNOWN")
    return "UNKNOWN"


def trigger_pipeline(
    component: Component,
    *,
    pipeline_id: str,
    branch: str,
    comment: str,
    wait: bool,
    dry_run: bool,
) -> dict[str, str]:
    if not pipeline_id or "," in pipeline_id:
        raise ReleaseError(f"Component {component.key} needs exactly one pipeline id")
    url = f"{YUNXIAO_ENDPOINT}/oapi/v1/flow/organizations/{ORG_ID}/pipelines/{pipeline_id}/runs"
    params: dict[str, Any] = {"comment": comment}
    if component.repo_url:
        params["runningBranchs"] = {component.repo_url: branch}
    body = {"params": json.dumps(params, ensure_ascii=False)}
    print(f"Yunxiao pipeline: {pipeline_id}")
    print(f"Source: {component.repo}@{branch}")
    if dry_run:
        print(f"DRY RUN POST {url}")
        return {"pipelineId": pipeline_id, "runId": "DRY_RUN", "status": "DRY_RUN"}
    response = request_json("POST", url, token=token_value(), body=body)
    run_id = extract_run_id(response)
    if not run_id:
        raise ReleaseError(f"Yunxiao returned no run id: {response}")
    result = {"pipelineId": pipeline_id, "runId": run_id, "status": "TRIGGERED"}
    print(f"Run: https://flow.aliyun.com/pipelines/{pipeline_id}/current (run {run_id})")
    if not wait:
        return result
    status_url = f"{url}/{run_id}"
    for _ in range(120):
        status = extract_status(request_json("GET", status_url, token=token_value())).upper()
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {component.key}: {status}")
        if status in {"SUCCESS", "SUCCEEDED"}:
            result["status"] = status
            return result
        if status in {"FAIL", "FAILED", "ERROR", "CANCELED", "CANCELLED"}:
            raise ReleaseError(f"Pipeline {pipeline_id} run {run_id} ended with {status}")
        time.sleep(15)
    raise ReleaseError(f"Timed out waiting for pipeline {pipeline_id} run {run_id}")


def health_check(url: str | None, *, dry_run: bool) -> None:
    if not url:
        return
    target = f"{url}{'&' if '?' in url else '?'}release_check={int(time.time())}"
    print(f"Health check: {target}")
    if dry_run:
        return
    request = urllib.request.Request(target, headers={"User-Agent": "beex-release/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status >= 400:
                raise ReleaseError(f"Health check failed: HTTP {response.status} {url}")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise ReleaseError(f"Health check failed for {url}: {exc}") from exc


def record_path(workspace: Path) -> Path:
    path = workspace / ".beex-release-records"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_record(workspace: Path, command: str, args: argparse.Namespace, result: Any) -> Path:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "recordedAt": now.isoformat(),
        "command": command,
        "arguments": {key: value for key, value in vars(args).items() if key not in {"func"}},
        "result": result,
    }
    path = record_path(workspace) / f"{now.strftime('%Y%m%dT%H%M%S.%fZ')}-{command}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Release record: {path}")
    return path


def env_code(value: str) -> str:
    mapping = {"test": "id-test", "prod": "id-prod", "production": "id-prod"}
    normalized = mapping.get(value.lower(), value.lower())
    if normalized not in {"id-test", "id-prod", "my-test", "my-prod"}:
        raise ReleaseError(f"Unsupported environment: {value}")
    return normalized


def is_prod(value: str) -> bool:
    return env_code(value).endswith("-prod")


def component_result(component: Component, snapshot: dict[str, str], execution: Any) -> dict[str, Any]:
    return {"component": component.key, "source": snapshot, "execution": execution}


def cmd_inventory(args: argparse.Namespace) -> Any:
    rows = []
    for component in COMPONENTS.values():
        path = args.workspace / component.repo
        rows.append({**asdict(component), "path": str(path), "exists": (path / ".git").is_dir()})
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return rows


def cmd_preflight(args: argparse.Namespace) -> Any:
    keys = args.components or list(COMPONENTS)
    results = []
    for key in keys:
        component = COMPONENTS.get(key)
        if not component:
            raise ReleaseError(f"Unknown component: {key}")
        results.append(repo_snapshot(repo_path(args.workspace, component), check_origin=args.check_origin, dry_run=args.dry_run))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


def cmd_h5(args: argparse.Namespace) -> Any:
    component = COMPONENTS["h5"]
    environment = env_code(args.env)
    if is_prod(environment):
        raise ReleaseError(
            "Do not rebuild H5 separately for production. Build one DRAFT in id-test, test it, then transfer "
            "the exact package to production from BeeX Admin."
        )
    path = repo_path(args.workspace, component)
    snapshot = release_snapshot(path, args)
    command = ["bash", "scripts/run-yunxiao-pipeline.sh", "--target", "release", "--branch", snapshot["branch"]]
    if args.no_wait:
        command.append("--no-wait")
    if args.comment:
        command.extend(["--comment", args.comment])
    environment_vars = {
        "H5_PACKAGE_ENV_CODE": environment,
        "H5_PACKAGE_COUNTRY_CODE": args.country,
        "H5_PACKAGE_STATUS": "DRAFT",
        "H5_PACKAGE_REGISTER": "true",
        "H5_REFRESH_CDN": "false",
    }
    if args.version:
        environment_vars["H5_PACKAGE_VERSION"] = args.version
    run(command, cwd=path, env=environment_vars, dry_run=args.dry_run)
    return component_result(component, snapshot, {"environment": environment, "status": "DRAFT", "version": args.version})


def native_backend_environment(args: argparse.Namespace) -> str:
    return env_code(args.backend_env or ("id-prod" if args.target == "prod" else "id-test"))


def native_build_environment(args: argparse.Namespace, version: str, build: str) -> dict[str, str]:
    environment = native_backend_environment(args)
    hosts = {
        "id-test": ("https://api-id-test.beexofficial.com", "https://h5-id-test.beexofficial.com/", "ID"),
        "id-prod": ("https://api-id.beexofficial.com", "https://h5-id.beexofficial.com/", "ID"),
        "my-test": ("https://api-my-test.beexofficial.com", "https://h5-my-test.beexofficial.com/", "MY"),
        "my-prod": ("https://api-my.beexofficial.com", "https://h5-my.beexofficial.com/", "MY"),
    }
    api_base, h5_base, country = hosts[environment]
    values = {
        "APP_VERSION": version,
        "BUILD_NUMBER": build,
        "API_BASE_URL": api_base,
        "H5_BASE_URL": h5_base,
        "H5_PACKAGE_ENV_CODE": environment,
        "COUNTRY_CODE": country,
        "BUNDLED_H5_SOURCE": args.h5_source,
    }
    if args.skip_h5:
        values["BEEX_SKIP_BUNDLED_H5_UPDATE"] = "1"
    if args.h5_zip:
        values.update({
            "BUNDLED_H5_SOURCE": "zip",
            "BEEX_BUNDLED_H5_ZIP": str(Path(args.h5_zip).expanduser().resolve()),
        })
    return values


def bundled_h5_info(path: Path, expected_version: str | None, *, dry_run: bool) -> dict[str, Any]:
    zip_path = path / "assets/h5/bootstrap/beex-h5.zip"
    if dry_run:
        return {"path": str(zip_path), "version": expected_version or "DRY_RUN", "dryRun": True}
    if not zip_path.is_file():
        raise ReleaseError(f"Bundled H5 package not found after build: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    version = str(manifest.get("h5Version") or manifest.get("version") or "unknown")
    if expected_version and version != expected_version:
        raise ReleaseError(f"Bundled H5 version mismatch: expected {expected_version}, got {version}")
    return {"path": str(zip_path), "version": version, "entry": manifest.get("entry") or "index.html"}


def artifact_info(path: Path, patterns: list[str], *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"patterns": patterns, "dryRun": True}
    candidates = [candidate for pattern in patterns for candidate in path.glob(pattern) if candidate.is_file()]
    if not candidates:
        raise ReleaseError(f"Build finished but no artifact matched: {', '.join(patterns)}")
    artifact = max(candidates, key=lambda candidate: candidate.stat().st_mtime)
    digest = hashlib.sha256()
    with artifact.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(artifact), "bytes": artifact.stat().st_size, "sha256": digest.hexdigest()}


def cmd_ios(args: argparse.Namespace) -> Any:
    component = COMPONENTS["native"]
    path = repo_path(args.workspace, component)
    snapshot = release_snapshot(path, args)
    target = args.target
    if target == "prod" and (not args.version or not args.build):
        raise ReleaseError("Production iOS releases require --version and --build")
    version = args.version or "88.88.88"
    build = args.build or dt.datetime.now().strftime("%y%m%d%H")
    args.version, args.build = version, build
    environment = native_build_environment(args, version, build)
    if args.upload:
        run(
            ["bash", "scripts/build_ios.sh", target, "ipa"],
            cwd=path,
            env={**environment, "EXPORT_METHOD": "app-store"},
            dry_run=args.dry_run,
        )
        h5 = bundled_h5_info(path, args.expected_h5_version, dry_run=args.dry_run)
        artifact = artifact_info(path, ["build/ios/ipa/*.ipa"], dry_run=args.dry_run)
        run(
            ["bash", "scripts/upload_ios_appstoreconnect.sh", target],
            cwd=path,
            env={**environment, "SKIP_BUILD": "1"},
            dry_run=args.dry_run,
        )
    else:
        run(["bash", "scripts/build_ios.sh", target, args.format], cwd=path, env=environment, dry_run=args.dry_run)
        h5 = bundled_h5_info(path, args.expected_h5_version, dry_run=args.dry_run)
        artifact = artifact_info(
            path,
            ["build/ios/ipa/*.ipa"] if args.format == "ipa" else ["build/ios/iphoneos/*.app/Runner"],
            dry_run=args.dry_run,
        )
    return component_result(component, snapshot, {
        "platform": "ios", "target": target, "backendEnvironment": native_backend_environment(args),
        "version": version, "build": build, "uploaded": args.upload, "bundledH5": h5, "artifact": artifact,
    })


def cmd_android(args: argparse.Namespace) -> Any:
    component = COMPONENTS["native"]
    path = repo_path(args.workspace, component)
    snapshot = release_snapshot(path, args)
    target = args.target
    if target == "prod" and (not args.version or not args.build):
        raise ReleaseError("Production Android releases require --version and --build")
    version = args.version or "88.88.88"
    build = args.build or dt.datetime.now().strftime("%y%m%d%H")
    if not build.isdigit() or int(build) > 2_100_000_000:
        raise ReleaseError("Android --build must be a positive integer no greater than 2100000000")
    args.version, args.build = version, build
    environment = native_build_environment(args, version, build)
    run(["bash", "scripts/build_android.sh", target, args.format], cwd=path, env=environment, dry_run=args.dry_run)
    h5 = bundled_h5_info(path, args.expected_h5_version, dry_run=args.dry_run)
    artifact = artifact_info(
        path,
        ["build/app/outputs/flutter-apk/*.apk"] if args.format == "apk" else ["build/app/outputs/bundle/release/*.aab"],
        dry_run=args.dry_run,
    )
    return component_result(component, snapshot, {
        "platform": "android", "target": target, "backendEnvironment": native_backend_environment(args),
        "version": version, "build": build, "format": args.format, "bundledH5": h5, "artifact": artifact,
    })


def cmd_service(args: argparse.Namespace) -> Any:
    component = COMPONENTS.get(args.component)
    if not component or component.kind not in {"service", "shared-service"}:
        raise ReleaseError(f"Unsupported service component: {args.component}")
    path = repo_path(args.workspace, component)
    snapshot = repo_snapshot(path, check_origin=not args.skip_origin_check, dry_run=args.dry_run)
    if component.kind == "shared-service":
        if args.env.lower() not in {"shared", "global"}:
            raise ReleaseError(f"{component.key} is a shared service; use --env shared")
        execution = trigger_pipeline(
            component,
            pipeline_id=str(component.test_pipeline or ""),
            branch=snapshot["branch"],
            comment=args.comment or f"Release shared {component.key} {snapshot['commit'][:8]}",
            wait=not args.no_wait,
            dry_run=args.dry_run,
        )
        health_check(component.health_test, dry_run=args.dry_run)
        return component_result(component, snapshot, execution)

    environment = env_code(args.env)
    if component.key == "business":
        if is_prod(environment):
            if not args.commit:
                raise ReleaseError("Production business release requires --commit with the tested SHA")
            commit = args.commit
            command = ["bash", "ci/promote-service-commit.sh", environment, "--commit", commit]
        else:
            command = ["bash", "ci/run-yunxiao-pipeline.sh", environment, "--branch", snapshot["branch"]]
        if args.no_wait:
            command.append("--no-wait")
        if args.comment:
            command.extend(["--comment", args.comment])
        run(command, cwd=path, dry_run=args.dry_run)
        execution: Any = {"environment": environment, "commit": args.commit or snapshot["commit"]}
    else:
        if is_prod(environment):
            if not args.commit:
                raise ReleaseError("Production admin-service release requires --commit with the tested SHA")
            if not args.dry_run and args.commit != snapshot["commit"]:
                raise ReleaseError(
                    f"admin-service working HEAD {snapshot['commit'][:8]} does not match tested commit {args.commit[:8]}"
                )
        pipeline = component.prod_pipeline if is_prod(environment) else component.test_pipeline
        execution = trigger_pipeline(
            component,
            pipeline_id=str(pipeline or ""),
            branch=snapshot["branch"],
            comment=args.comment or f"Release {component.key} {environment} {snapshot['commit'][:8]}",
            wait=not args.no_wait,
            dry_run=args.dry_run,
        )
    health_check(component.health_prod if is_prod(environment) else component.health_test, dry_run=args.dry_run)
    return component_result(component, snapshot, execution)


def cmd_web(args: argparse.Namespace) -> Any:
    component = COMPONENTS.get(args.component)
    if not component or component.kind not in {"web", "static"}:
        raise ReleaseError(f"Unsupported web component: {args.component}")
    path = repo_path(args.workspace, component)
    snapshot = repo_snapshot(path, check_origin=not args.skip_origin_check, dry_run=args.dry_run)
    if component.key == "admin-page":
        command = ["bash", "scripts/run-yunxiao-pipeline.sh", "--branch", snapshot["branch"]]
        if args.no_wait:
            command.append("--no-wait")
        if args.comment:
            command.extend(["--comment", args.comment])
        run(command, cwd=path, dry_run=args.dry_run)
        execution: Any = {"pipelineId": component.test_pipeline}
    else:
        if not args.allow_direct_static:
            raise ReleaseError(
                f"{component.key} has no Yunxiao release pipeline yet. Re-run with --allow-direct-static "
                "only when the controlled OSS/CDN script is intentionally approved."
            )
        script = path / "scripts/deploy-oss-cdn.sh"
        if not script.is_file():
            raise ReleaseError(f"Controlled deploy script not found: {script}")
        run(["bash", str(script.relative_to(path))], cwd=path, dry_run=args.dry_run)
        execution = {"mode": "controlled-direct-static"}
    health_check(component.health_prod, dry_run=args.dry_run)
    return component_result(component, snapshot, execution)


def cmd_verify_h5(args: argparse.Namespace) -> Any:
    environment = env_code(args.env)
    api_base = {
        "id-test": "https://api-id-test.beexofficial.com",
        "id-prod": "https://api-id.beexofficial.com",
        "my-test": "https://api-my-test.beexofficial.com",
        "my-prod": "https://api-my.beexofficial.com",
    }[environment]
    query = (
        f"countryCode={args.country}&envCode={environment}&platform={args.platform}"
        f"&nativeVersion={args.native_version}&buildNumber={args.build}&packageName={args.package_name}"
        f"&currentH5Version={args.current_version}"
    )
    url = f"{api_base}/api/v1/app/h5-package/latest?{query}"
    print(f"GET {url}")
    if args.dry_run:
        return {"url": url, "dryRun": True}
    payload = request_json("GET", url)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.expected_version and args.expected_version not in json.dumps(payload, ensure_ascii=False):
        raise ReleaseError(f"Expected H5 version {args.expected_version} was not returned")
    return payload


def self_command(args: argparse.Namespace, parts: list[str]) -> None:
    command = [sys.executable, str(Path(__file__).resolve()), "--workspace", str(args.workspace), *parts]
    if args.dry_run:
        command.append("--dry-run")
    run(command, dry_run=False)


def cmd_all(args: argparse.Namespace) -> Any:
    results: list[dict[str, Any]] = []
    if args.phase == "test":
        steps = [
            ["h5", "--env", "id-test"],
            ["service", "business", "--env", "id-test"],
            ["service", "admin-service", "--env", "id-test"],
            ["web", "admin-page"],
        ]
        if args.include_shared:
            steps[3:3] = [
                ["service", "sso", "--env", "shared"],
                ["service", "ai-worker", "--env", "shared"],
            ]
        if args.include_static:
            steps.extend([
                ["web", "docs", "--allow-direct-static"],
                ["web", "official-site", "--allow-direct-static"],
            ])
    elif args.phase == "prod":
        if not args.service_commit or not args.admin_service_commit or not args.h5_version:
            raise ReleaseError(
                "Production full release requires --service-commit, --admin-service-commit, and --h5-version "
                "from the tested release"
            )
        steps = [
            ["service", "business", "--env", "id-prod", "--commit", args.service_commit],
            ["service", "admin-service", "--env", "id-prod", "--commit", args.admin_service_commit],
            ["web", "admin-page"],
        ]
        if args.include_shared:
            steps[2:2] = [
                ["service", "sso", "--env", "shared"],
                ["service", "ai-worker", "--env", "shared"],
            ]
        if args.include_static:
            steps.extend([
                ["web", "docs", "--allow-direct-static"],
                ["web", "official-site", "--allow-direct-static"],
            ])
        print(
            "H5 production is intentionally not rebuilt here. Transfer, gray, and publish the exact tested "
            f"package {args.h5_version or '<required package>'} in BeeX Admin."
        )
    else:
        if not args.h5_version:
            raise ReleaseError("Native full release requires --h5-version for traceability")
        if not args.version or not args.build:
            raise ReleaseError("Native full release requires --version and --build")
        if not args.build.isdigit() or int(args.build) > 2_100_000_000:
            raise ReleaseError("Native full release --build must be Android-compatible (1..2100000000)")
        native_path = repo_path(args.workspace, COMPONENTS["native"])
        native_snapshot = repo_snapshot(native_path, check_origin=True, dry_run=args.dry_run)
        android_format = args.android_format or ("aab" if args.target == "prod" else "apk")
        steps = [
            ["ios", "--target", args.target, "--backend-env", args.backend_env, "--version", args.version,
             "--build", args.build, "--expected-h5-version", args.h5_version, "--upload",
             "--internal-preflight-commit", native_snapshot["commit"]],
            ["android", "--target", args.target, "--backend-env", args.backend_env, "--version", args.version,
             "--build", args.build, "--expected-h5-version", args.h5_version, "--format", android_format,
             "--h5-source", "zip", "--h5-zip", str(native_path / "assets/h5/bootstrap/beex-h5.zip"),
             "--internal-preflight-commit", native_snapshot["commit"]],
        ]
    for parts in steps:
        print(f"\n=== {' '.join(parts)} ===", flush=True)
        self_command(args, parts)
        results.append({"step": parts, "status": "DRY_RUN" if args.dry_run else "SUCCESS"})
    return {"phase": args.phase, "steps": results, "h5Version": args.h5_version}


def add_common_release_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Print commands without publishing")
    parser.add_argument("--skip-origin-check", action="store_true", help="Skip exact origin HEAD check (not recommended)")
    parser.add_argument("--internal-preflight-commit", help=argparse.SUPPRESS)


def add_native_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", choices=("test", "prod"), default="test")
    parser.add_argument("--backend-env", choices=("id-test", "id-prod", "my-test", "my-prod"))
    parser.add_argument("--version")
    parser.add_argument("--build")
    parser.add_argument("--expected-h5-version")
    parser.add_argument("--h5-source", choices=("remote", "local", "zip", "auto"), default="remote")
    parser.add_argument("--h5-zip")
    parser.add_argument("--skip-h5", action="store_true")
    add_common_release_flags(parser)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="beex-release", description="Guarded BeeX release orchestrator")
    root.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    commands = root.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser("inventory", help="Show release components and pipelines")
    inventory.set_defaults(func=cmd_inventory)

    preflight = commands.add_parser("preflight", help="Validate repository release state")
    preflight.add_argument("components", nargs="*", choices=tuple(COMPONENTS))
    preflight.add_argument("--check-origin", action="store_true")
    preflight.add_argument("--dry-run", action="store_true")
    preflight.set_defaults(func=cmd_preflight)

    h5 = commands.add_parser("h5", help="Build and register one H5 DRAFT in test")
    h5.add_argument("--env", default="id-test")
    h5.add_argument("--country", default="ID")
    h5.add_argument("--version")
    h5.add_argument("--comment")
    h5.add_argument("--no-wait", action="store_true")
    add_common_release_flags(h5)
    h5.set_defaults(func=cmd_h5)

    ios = commands.add_parser("ios", help="Build or upload the iOS app")
    add_native_flags(ios)
    ios.add_argument("--format", choices=("ios", "ipa"), default="ipa")
    ios.add_argument("--upload", action="store_true")
    ios.set_defaults(func=cmd_ios)

    android = commands.add_parser("android", help="Build an Android APK or AAB")
    add_native_flags(android)
    android.add_argument("--format", choices=("apk", "aab"), default="apk")
    android.set_defaults(func=cmd_android)

    service = commands.add_parser("service", help="Release one backend service")
    service.add_argument("component", choices=("business", "admin-service", "sso", "ai-worker"))
    service.add_argument("--env", default="id-test")
    service.add_argument("--commit", help="Exact tested commit for business production promotion")
    service.add_argument("--comment")
    service.add_argument("--no-wait", action="store_true")
    add_common_release_flags(service)
    service.set_defaults(func=cmd_service)

    web = commands.add_parser("web", help="Publish a web property")
    web.add_argument("component", choices=("admin-page", "docs", "official-site"))
    web.add_argument("--comment")
    web.add_argument("--no-wait", action="store_true")
    web.add_argument("--allow-direct-static", action="store_true")
    add_common_release_flags(web)
    web.set_defaults(func=cmd_web)

    verify = commands.add_parser("verify-h5", help="Query the app H5 latest API")
    verify.add_argument("--env", default="id-test")
    verify.add_argument("--country", default="ID")
    verify.add_argument("--platform", choices=("ALL", "IOS", "ANDROID"), default="ALL")
    verify.add_argument("--native-version", default="88.88.88")
    verify.add_argument("--build", default="1")
    verify.add_argument("--package-name", default="com.beexofficial.x")
    verify.add_argument("--current-version", default="none")
    verify.add_argument("--expected-version")
    verify.add_argument("--dry-run", action="store_true")
    verify.set_defaults(func=cmd_verify_h5)

    all_release = commands.add_parser("all", help="Run a gated release phase")
    all_release.add_argument("--phase", choices=("test", "prod", "native"), required=True)
    all_release.add_argument("--service-commit")
    all_release.add_argument("--admin-service-commit")
    all_release.add_argument("--h5-version")
    all_release.add_argument("--target", choices=("test", "prod"), default="test")
    all_release.add_argument("--backend-env", choices=("id-test", "id-prod", "my-test", "my-prod"), default="id-test")
    all_release.add_argument("--version")
    all_release.add_argument("--build")
    all_release.add_argument("--include-shared", action="store_true")
    all_release.add_argument("--include-static", action="store_true")
    all_release.add_argument("--android-format", choices=("apk", "aab"))
    all_release.add_argument("--dry-run", action="store_true")
    all_release.set_defaults(func=cmd_all)
    return root


def main() -> int:
    args = parser().parse_args()
    args.workspace = args.workspace.expanduser().resolve()
    try:
        result = args.func(args)
        if args.command not in {"inventory", "preflight", "verify-h5"}:
            write_record(args.workspace, args.command, args, result)
        return 0
    except (ReleaseError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
