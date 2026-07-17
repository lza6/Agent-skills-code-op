from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO_ROOT / "release" / "build_release.py"
METADATA_PATH = REPO_ROOT / "release" / "metadata.json"
SKILL_DIR = REPO_ROOT / "skills" / "production-delivery-orchestrator"
TEST_COMMIT = "a" * 40


def load_builder_module() -> object:
    spec = importlib.util.spec_from_file_location("release_builder_test_module", BUILD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Release 构建器")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_builder_module()
        self.metadata = self.builder.load_metadata(METADATA_PATH)

    def test_build_is_deterministic_and_self_verifying(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-release-builder-") as temp:
            root = Path(temp)
            first = self.builder.build_release(
                self.metadata, SKILL_DIR, root / "first", TEST_COMMIT, METADATA_PATH
            )
            second = self.builder.build_release(
                self.metadata, SKILL_DIR, root / "second", TEST_COMMIT, METADATA_PATH
            )
            self.builder.verify_release(self.metadata, root / "first")
            self.builder.verify_release(self.metadata, root / "second")
            for key in ("zip", "provenance", "checksums"):
                self.assertEqual(first[key].read_bytes(), second[key].read_bytes(), key)

    def test_verifier_rejects_tampered_zip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-release-tamper-") as temp:
            output = Path(temp) / "out"
            assets = self.builder.build_release(
                self.metadata, SKILL_DIR, output, TEST_COMMIT, METADATA_PATH
            )
            with assets["zip"].open("ab") as handle:
                handle.write(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "校验和不匹配"):
                self.builder.verify_release(self.metadata, output)

    def test_metadata_rejects_non_release_semver_and_missing_attestation(self) -> None:
        broken = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        broken["version"] = "1.2.0-rc.1"
        with self.assertRaisesRegex(RuntimeError, "三段 SemVer"):
            self.builder.validate_metadata(broken)
        broken = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        del broken["attestation"]
        with self.assertRaisesRegex(RuntimeError, "attestation"):
            self.builder.validate_metadata(broken)

    def test_manifest_matches_forward_harness_canonical_hash(self) -> None:
        manifest, builder_hash = self.builder.artifact_manifest(SKILL_DIR)
        self.assertGreater(len(manifest), 0)
        forward_path = (
            REPO_ROOT / "evals" / "production-delivery-orchestrator" / "run_forward_tests.py"
        )
        spec = importlib.util.spec_from_file_location("forward_hash_test_module", forward_path)
        if spec is None or spec.loader is None:
            self.fail("无法加载 forward harness")
        forward = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(forward)
        self.assertEqual(builder_hash, forward.skill_artifact_sha256(SKILL_DIR))


if __name__ == "__main__":
    unittest.main()
