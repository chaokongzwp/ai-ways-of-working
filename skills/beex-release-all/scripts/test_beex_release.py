from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("beex_release.py")
SPEC = importlib.util.spec_from_file_location("beex_release", MODULE_PATH)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)


class ReleaseScriptTest(unittest.TestCase):
    def test_environment_aliases(self) -> None:
        self.assertEqual(release.env_code("test"), "id-test")
        self.assertEqual(release.env_code("production"), "id-prod")
        self.assertTrue(release.is_prod("id-prod"))
        with self.assertRaises(release.ReleaseError):
            release.env_code("unknown")

    def test_shared_services_have_no_fake_production_pipeline(self) -> None:
        self.assertEqual(release.COMPONENTS["sso"].kind, "shared-service")
        self.assertIsNone(release.COMPONENTS["sso"].prod_pipeline)
        self.assertEqual(release.COMPONENTS["ai-worker"].kind, "shared-service")
        self.assertIsNone(release.COMPONENTS["ai-worker"].prod_pipeline)

    def test_native_backend_environment_is_explicit(self) -> None:
        args = argparse.Namespace(
            backend_env="id-test",
            target="prod",
            h5_source="remote",
            skip_h5=False,
            h5_zip=None,
        )
        values = release.native_build_environment(args, "1.0.0", "26071301")
        self.assertEqual(values["API_BASE_URL"], "https://api-id-test.beexofficial.com")
        self.assertEqual(values["H5_PACKAGE_ENV_CODE"], "id-test")
        self.assertEqual(values["APP_VERSION"], "1.0.0")

    def test_bundled_h5_version_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "assets/h5/bootstrap/beex-h5.zip"
            package.parent.mkdir(parents=True)
            manifest = {"h5Version": "h5-test-1", "entry": "index.html"}
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr("index.html", "ok")

            info = release.bundled_h5_info(root, "h5-test-1", dry_run=False)
            self.assertEqual(info["version"], "h5-test-1")
            with self.assertRaises(release.ReleaseError):
                release.bundled_h5_info(root, "different", dry_run=False)

    def test_artifact_info_records_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "build/app/outputs/flutter-apk/app-release.apk"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"beex")
            info = release.artifact_info(root, ["build/app/outputs/flutter-apk/*.apk"], dry_run=False)
            self.assertEqual(info["bytes"], 4)
            self.assertEqual(info["sha256"], hashlib.sha256(b"beex").hexdigest())

    def test_full_release_parser_accepts_all_gates(self) -> None:
        args = release.parser().parse_args([
            "all",
            "--phase",
            "prod",
            "--service-commit",
            "a" * 40,
            "--admin-service-commit",
            "b" * 40,
            "--h5-version",
            "h5-test-1",
            "--include-shared",
        ])
        self.assertEqual(args.phase, "prod")
        self.assertTrue(args.include_shared)


if __name__ == "__main__":
    unittest.main()
