#!/usr/bin/env python3
"""从单一发布元数据构建、校验并记录确定性的技能 Release 制品。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA = REPO_ROOT / "release" / "metadata.json"
ARTIFACT_DOMAIN = b"production-delivery-orchestrator-artifact-v2\0"
TEXT_KIND = b"T"
BINARY_KIND = b"B"
IGNORED_DIRECTORIES = {"__pycache__"}
IGNORED_FILES = {".DS_Store"}
IGNORED_SUFFIXES = {".pyc"}
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SOURCE_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="根据 release/metadata.json 构建并校验版本化技能制品。"
    )
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "dist")
    parser.add_argument(
        "--commit",
        help="写入 provenance 的提交 SHA；默认读取当前仓库 HEAD。",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="仅校验已有制品，不执行构建。",
    )
    return parser.parse_args()


def load_metadata(path: Path) -> dict[str, Any]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"发布元数据不存在：{path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"发布元数据不是有效 JSON：{path}: {error}") from error
    if not isinstance(metadata, dict):
        raise RuntimeError("发布元数据根节点必须为对象")
    validate_metadata(metadata)
    return metadata


def validate_metadata(metadata: dict[str, Any]) -> None:
    required_strings = (
        "skill",
        "version",
        "tag",
        "title",
        "previous_release",
        "release_notes",
        "source_date",
    )
    if metadata.get("schema") != 1:
        raise RuntimeError("发布元数据 schema 必须为 1")
    for key in required_strings:
        if not isinstance(metadata.get(key), str) or not metadata[key]:
            raise RuntimeError(f"发布元数据缺少非空字符串字段：{key}")
    if not SEMVER_RE.fullmatch(metadata["version"]):
        raise RuntimeError("version 必须是无预发布/构建后缀的三段 SemVer")
    if metadata["tag"] != f"v{metadata['version']}":
        raise RuntimeError("tag 必须等于 v<version>")
    if not SOURCE_DATE_RE.fullmatch(metadata["source_date"]):
        raise RuntimeError("source_date 必须为 YYYY-MM-DD")

    compatibility = metadata.get("compatibility")
    if not isinstance(compatibility, dict):
        raise RuntimeError("compatibility 必须为对象")
    for key in ("native_targets", "bridge_targets"):
        values = compatibility.get(key)
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value for value in values
        ):
            raise RuntimeError(f"compatibility.{key} 必须为非空字符串数组")

    attestation = metadata.get("attestation")
    if not isinstance(attestation, dict):
        raise RuntimeError("attestation 必须为对象")
    if attestation.get("provider") != "github-attestation":
        raise RuntimeError("attestation.provider 必须为 github-attestation")
    if attestation.get("required") is not True:
        raise RuntimeError("attestation.required 必须为 true")
    if attestation.get("subject") != "release-zip":
        raise RuntimeError("attestation.subject 必须为 release-zip")
    if not isinstance(attestation.get("verify_command"), str):
        raise RuntimeError("attestation.verify_command 必须为字符串")


def artifact_file_paths(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        raise RuntimeError(f"技能源目录不存在或不是目录：{source_dir}")
    files: list[Path] = []
    for root, directory_names, file_names in os.walk(source_dir, topdown=True):
        root_path = Path(root)
        kept_directories: list[str] = []
        for name in directory_names:
            path = root_path / name
            if name in IGNORED_DIRECTORIES:
                continue
            if path.is_symlink():
                raise RuntimeError(f"制品不允许符号链接目录：{path}")
            kept_directories.append(name)
        directory_names[:] = kept_directories
        for name in file_names:
            path = root_path / name
            if name in IGNORED_FILES or path.suffix.lower() in IGNORED_SUFFIXES:
                continue
            if path.is_symlink():
                raise RuntimeError(f"制品不允许符号链接文件：{path}")
            if stat.S_ISREG(path.lstat().st_mode):
                files.append(path)
    return sorted(files, key=lambda path: path.relative_to(source_dir).as_posix())


def canonical_content(content: bytes) -> tuple[bytes, bytes]:
    if b"\0" in content:
        return BINARY_KIND, content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return BINARY_KIND, content
    return TEXT_KIND, text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_artifact_sha256(files: Iterable[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    digest.update(ARTIFACT_DOMAIN)
    for relative_path, raw_content in files:
        path_bytes = relative_path.encode("utf-8")
        kind, content = canonical_content(raw_content)
        digest.update(len(path_bytes).to_bytes(8, byteorder="big"))
        digest.update(path_bytes)
        digest.update(kind)
        digest.update(len(content).to_bytes(8, byteorder="big"))
        digest.update(content)
    return digest.hexdigest()


def artifact_manifest(source_dir: Path) -> tuple[list[dict[str, Any]], str]:
    entries: list[dict[str, Any]] = []
    hash_inputs: list[tuple[str, bytes]] = []
    for path in artifact_file_paths(source_dir):
        relative_path = path.relative_to(source_dir).as_posix()
        raw_content = path.read_bytes()
        kind, canonical = canonical_content(raw_content)
        entries.append(
            {
                "path": relative_path,
                "size": len(raw_content),
                "raw_sha256": hashlib.sha256(raw_content).hexdigest(),
                "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
                "content_kind": "utf8-text" if kind == TEXT_KIND else "binary",
            }
        )
        hash_inputs.append((relative_path, raw_content))
    return entries, canonical_artifact_sha256(hash_inputs)


def source_date_tuple(value: str) -> tuple[int, int, int, int, int, int]:
    match = SOURCE_DATE_RE.fullmatch(value)
    if match is None:
        raise RuntimeError("source_date 必须为 YYYY-MM-DD")
    year, month, day = (int(part) for part in match.groups())
    try:
        # zip 格式最早可表示 1980 年，显式校验日期有效性。
        __import__("datetime").date(year, month, day)
    except ValueError as error:
        raise RuntimeError("source_date 不是有效日期") from error
    if year < 1980:
        raise RuntimeError("source_date 不能早于 ZIP 格式支持的 1980 年")
    return year, month, day, 0, 0, 0


def write_deterministic_zip(
    source_dir: Path,
    destination: Path,
    source_date: str,
) -> None:
    date_time = source_date_tuple(source_date)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in artifact_file_paths(source_dir):
                relative_path = path.relative_to(source_dir).as_posix()
                info = zipfile.ZipInfo(f"{source_dir.name}/{relative_path}", date_time)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "无法读取当前 Git 提交")
    return result.stdout.strip()


def artifact_names(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        "zip": f"{metadata['skill']}-{metadata['tag']}.zip",
        "provenance": "provenance.json",
        "checksums": "SHA256SUMS.txt",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_release(
    metadata: dict[str, Any],
    source_dir: Path,
    output_dir: Path,
    commit: str,
    metadata_path: Path,
) -> dict[str, Path]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("commit 必须是 40 位小写 Git SHA")
    source_dir = source_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    names = artifact_names(metadata)
    zip_path = output_dir / names["zip"]
    provenance_path = output_dir / names["provenance"]
    checksum_path = output_dir / names["checksums"]

    manifest, canonical_hash = artifact_manifest(source_dir)
    write_deterministic_zip(source_dir, zip_path, metadata["source_date"])
    provenance = {
        "schema": 2,
        "skill": metadata["skill"],
        "version": metadata["version"],
        "tag": metadata["tag"],
        "commit": commit,
        "source_date": metadata["source_date"],
        "metadata_sha256": sha256_file(metadata_path),
        "artifact": {
            "zip": names["zip"],
            "canonical_sha256": canonical_hash,
            "file_count": len(manifest),
            "files": manifest,
        },
        "attestation": metadata["attestation"],
    }
    write_json(provenance_path, provenance)
    checksum_path.write_text(
        f"{sha256_file(zip_path)} *{zip_path.name}\n"
        f"{sha256_file(provenance_path)} *{provenance_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"zip": zip_path, "provenance": provenance_path, "checksums": checksum_path}


def parse_checksums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64}) \*(.+)", line)
        if match is None:
            raise RuntimeError(f"校验和格式无效：{line}")
        digest, name = match.groups()
        if name in entries:
            raise RuntimeError(f"校验和重复条目：{name}")
        entries[name] = digest
    return entries


def verify_release(metadata: dict[str, Any], output_dir: Path) -> None:
    names = artifact_names(metadata)
    paths = {key: output_dir / name for key, name in names.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"缺少制品：{', '.join(missing)}")

    checksums = parse_checksums(paths["checksums"])
    expected_checksum_names = {paths["zip"].name, paths["provenance"].name}
    if set(checksums) != expected_checksum_names:
        raise RuntimeError("SHA256SUMS.txt 的制品集合不正确")
    for key in ("zip", "provenance"):
        path = paths[key]
        if checksums[path.name] != sha256_file(path):
            raise RuntimeError(f"校验和不匹配：{path.name}")

    provenance = json.loads(paths["provenance"].read_text(encoding="utf-8"))
    for key in ("schema", "skill", "version", "tag", "source_date", "attestation"):
        expected = 2 if key == "schema" else metadata[key]
        if provenance.get(key) != expected:
            raise RuntimeError(f"provenance 字段不匹配：{key}")
    artifact = provenance.get("artifact")
    if not isinstance(artifact, dict) or artifact.get("zip") != paths["zip"].name:
        raise RuntimeError("provenance artifact 信息无效")
    files = artifact.get("files")
    if not isinstance(files, list):
        raise RuntimeError("provenance 缺少 files manifest")

    expected_names = [f"{metadata['skill']}/{entry['path']}" for entry in files]
    with zipfile.ZipFile(paths["zip"]) as archive:
        names_in_zip = archive.namelist()
        if names_in_zip != expected_names or len(set(names_in_zip)) != len(names_in_zip):
            raise RuntimeError("ZIP 成员与 provenance manifest 不一致")
        hash_inputs: list[tuple[str, bytes]] = []
        for entry, zip_name in zip(files, names_in_zip, strict=True):
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise RuntimeError("provenance manifest 项无效")
            content = archive.read(zip_name)
            if entry.get("size") != len(content):
                raise RuntimeError(f"ZIP 文件大小不匹配：{zip_name}")
            if entry.get("raw_sha256") != hashlib.sha256(content).hexdigest():
                raise RuntimeError(f"ZIP 文件哈希不匹配：{zip_name}")
            hash_inputs.append((entry["path"], content))
    if artifact.get("canonical_sha256") != canonical_artifact_sha256(hash_inputs):
        raise RuntimeError("ZIP canonical artifact hash 不匹配")


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    metadata_path = args.metadata.resolve()
    metadata = load_metadata(metadata_path)
    source_dir = (args.source_dir or (REPO_ROOT / "skills" / metadata["skill"])).resolve()
    output_dir = args.output_dir.resolve()
    if args.verify:
        verify_release(metadata, output_dir)
        print(f"PASS: 已校验 {metadata['tag']} 的 Release 制品")
        return 0

    commit = args.commit or git_commit()
    assets = build_release(metadata, source_dir, output_dir, commit, metadata_path)
    print(f"PASS: 已构建 {metadata['tag']} 制品")
    for path in assets.values():
        print(path.name)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(1)
