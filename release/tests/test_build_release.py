from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


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
            self.builder.verify_release(
                self.metadata, root / "first", METADATA_PATH, TEST_COMMIT
            )
            self.builder.verify_release(
                self.metadata, root / "second", METADATA_PATH, TEST_COMMIT
            )
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

    def test_verifier_rejects_tampered_provenance_claims_after_checksum_rewrite(
        self,
    ) -> None:
        cases = (
            ("commit", "b" * 40, "commit 与预期提交"),
            ("metadata_sha256", "0" * 64, "metadata SHA-256"),
            ("artifact.file_count", 999, "file_count"),
        )
        with tempfile.TemporaryDirectory(prefix="pdo-provenance-tamper-") as temp:
            root = Path(temp)
            for index, (field, value, expected_error) in enumerate(cases):
                with self.subTest(field=field):
                    output = root / str(index)
                    assets = self.builder.build_release(
                        self.metadata, SKILL_DIR, output, TEST_COMMIT, METADATA_PATH
                    )
                    provenance = json.loads(
                        assets["provenance"].read_text(encoding="utf-8")
                    )
                    if field == "artifact.file_count":
                        provenance["artifact"]["file_count"] = value
                    else:
                        provenance[field] = value
                    assets["provenance"].write_text(
                        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    assets["checksums"].write_text(
                        f"{self.builder.sha256_file(assets['zip'])} *{assets['zip'].name}\n"
                        f"{self.builder.sha256_file(assets['provenance'])} *{assets['provenance'].name}\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    with self.assertRaisesRegex(RuntimeError, expected_error):
                        self.builder.verify_release(
                            self.metadata, output, METADATA_PATH, TEST_COMMIT
                        )

    def test_verifier_rejects_zip_resource_limits_after_checksum_rewrite(self) -> None:
        cases = (
            ("too-many-members", "ZIP 成员数量超过限制", "MAX_ZIP_MEMBERS", 2),
            (
                "single-member-size",
                "ZIP 成员未压缩大小超过限制",
                "MAX_ZIP_MEMBER_UNCOMPRESSED_SIZE",
                10,
            ),
            (
                "total-size",
                "ZIP 总未压缩大小超过限制",
                "MAX_ZIP_TOTAL_UNCOMPRESSED_SIZE",
                10,
            ),
            (
                "suspicious-compression",
                "ZIP 成员压缩比超过限制",
                "MAX_ZIP_COMPRESSION_RATIO",
                2,
            ),
        )
        with tempfile.TemporaryDirectory(prefix="pdo-zip-limits-") as temp:
            root = Path(temp)
            for case, expected_error, limit_name, limit_value in cases:
                with self.subTest(case=case):
                    output = root / case
                    assets = self.builder.build_release(
                        self.metadata, SKILL_DIR, output, TEST_COMMIT, METADATA_PATH
                    )
                    with patch.object(self.builder, limit_name, limit_value):
                        with zipfile.ZipFile(
                            assets["zip"], "w", compression=zipfile.ZIP_STORED
                        ) as archive:
                            if case == "too-many-members":
                                for index in range(limit_value + 1):
                                    archive.writestr(
                                        f"{self.metadata['skill']}/member-{index}.txt", b"x"
                                    )
                            elif case == "single-member-size":
                                archive.writestr(
                                    f"{self.metadata['skill']}/large.bin", b"x" * 11
                                )
                            elif case == "total-size":
                                for index in range(3):
                                    archive.writestr(
                                        f"{self.metadata['skill']}/part-{index}.bin", b"x" * 4
                                    )
                            else:
                                archive.writestr(
                                    f"{self.metadata['skill']}/compressible.bin",
                                    b"\0" * 1024,
                                    compress_type=zipfile.ZIP_DEFLATED,
                                )
                        assets["checksums"].write_text(
                            f"{self.builder.sha256_file(assets['zip'])} *{assets['zip'].name}\n"
                            f"{self.builder.sha256_file(assets['provenance'])} *{assets['provenance'].name}\n",
                            encoding="utf-8",
                            newline="\n",
                        )
                        with self.assertRaisesRegex(RuntimeError, expected_error):
                            self.builder.verify_release(self.metadata, output)

    def test_verifier_reads_zip_members_in_bounded_chunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-zip-chunked-read-") as temp:
            assets = self.builder.build_release(
                self.metadata, SKILL_DIR, Path(temp), TEST_COMMIT, METADATA_PATH
            )
            original_read = zipfile.ZipExtFile.read
            requested_sizes: list[int] = []

            def tracked_read(handle: zipfile.ZipExtFile, size: int = -1) -> bytes:
                requested_sizes.append(size)
                return original_read(handle, size)

            with patch.object(zipfile.ZipExtFile, "read", new=tracked_read):
                self.builder.verify_release(self.metadata, assets["zip"].parent)

            self.assertTrue(requested_sizes)
            self.assertTrue(
                all(size == self.builder.ZIP_READ_CHUNK_SIZE for size in requested_sizes)
            )

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
