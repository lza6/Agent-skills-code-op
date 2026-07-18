#!/usr/bin/env python3
"""Generate a narrow, reproducible dependency and action-pin inventory.

This is intentionally not a CycloneDX SBOM.  It records only repository
dependency-manifest boundaries and GitHub Action revisions observed in tracked
workflow YAML files.  It does not inspect dependency contents or emit workflow
values such as environment variables and secrets.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
FULL_SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
USES_PATTERN = re.compile(
    r"^\s*(?:-\s+)?uses\s*:\s+(?P<action>[^@\s]+)@(?P<reference>[^\s#]+)\s*$"
)
USES_KEY_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])uses\s*:")
DEPENDENCY_MANIFEST_NAMES = frozenset(
    {
        "Cargo.lock",
        "Cargo.toml",
        "Gemfile",
        "Gemfile.lock",
        "Pipfile",
        "Pipfile.lock",
        "composer.json",
        "composer.lock",
        "go.mod",
        "go.sum",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "uv.lock",
        "yarn.lock",
    }
)


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def git_tracked_paths(root: Path) -> list[str]:
    """Return portable paths Git marks as tracked, without reading their contents."""

    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="backslashreplace").strip()
        raise ValueError(f"无法读取 Git 受版本控制文件：{message or root}")
    return sorted(
        path.decode("utf-8", errors="surrogateescape")
        for path in result.stdout.split(b"\0")
        if path
    )


def tracked_workflow_paths(root: Path) -> list[Path]:
    workflow_prefix = ".github/workflows/"
    paths: list[Path] = []
    for relative in git_tracked_paths(root):
        portable = PurePosixPath(relative)
        if not relative.startswith(workflow_prefix) or portable.suffix not in {".yml", ".yaml"}:
            continue
        path = root / portable
        if path.is_file() and not path.is_symlink():
            paths.append(path)
    return paths


def dependency_manifest_paths(root: Path) -> list[str]:
    """Return tracked manifest/lockfile paths based on filenames alone."""

    return [
        relative
        for relative in git_tracked_paths(root)
        if PurePosixPath(relative).name in DEPENDENCY_MANIFEST_NAMES
    ]


def actions_from_workflow(root: Path, workflow: Path) -> list[dict[str, str]]:
    relative_workflow = workflow.relative_to(root).as_posix()
    actions: list[dict[str, str]] = []
    try:
        lines = workflow.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError(f"{relative_workflow}: 工作流必须是 UTF-8") from error

    for line_number, line in enumerate(lines, start=1):
        code = line.split("#", 1)[0].rstrip()
        if USES_KEY_PATTERN.search(code) is None:
            continue
        if "{" in code or "}" in code:
            raise ValueError(
                f"{relative_workflow}:{line_number}: 不支持 flow-style uses；请使用块式 - uses: action@<40位SHA>"
            )
        match = USES_PATTERN.match(code)
        if match is None:
            raise ValueError(
                f"{relative_workflow}:{line_number}: 无法安全解析 uses；请使用块式 - uses: action@<40位SHA>"
            )
        reference = match["reference"]
        if FULL_SHA_PATTERN.fullmatch(reference) is None:
            raise ValueError(
                f"{relative_workflow}:{line_number}: {match['action']} 必须固定到完整 40 位 SHA"
            )
        actions.append(
            {
                "action": match["action"],
                "sha": reference,
                "workflow": relative_workflow,
            }
        )
    return actions


def build_inventory(root: Path) -> dict[str, Any]:
    """Build deterministic inventory from tracked filenames and workflow action lines."""

    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"仓库根目录不存在或不是目录：{root}")
    manifests = dependency_manifest_paths(resolved_root)
    actions: list[dict[str, str]] = []
    for workflow in tracked_workflow_paths(resolved_root):
        actions.extend(actions_from_workflow(resolved_root, workflow))
    return {
        "dependency_manifests": manifests,
        "github_actions": sorted(
            actions, key=lambda item: (item["workflow"], item["action"], item["sha"])
        ),
        "python": {"runtime": "stdlib-only", "third_party_dependencies": "none"},
        "schema": SCHEMA_VERSION,
    }


def inventory_json(inventory: dict[str, Any]) -> str:
    return json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_inventory(root: Path, output: Path) -> dict[str, Any]:
    inventory = build_inventory(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(inventory_json(inventory), encoding="utf-8", newline="\n")
    return inventory


def inventory_matches(root: Path, output: Path) -> bool:
    try:
        actual = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return actual == build_inventory(root)


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成可重建的依赖和 GitHub Action 固定版本盘点。")
    parser.add_argument("--root", type=Path, default=default_root(), help="仓库根目录")
    parser.add_argument("--output", type=Path, help="输出路径（默认 docs/dependency-inventory.json）")
    parser.add_argument("--check", action="store_true", help="检查已生成 inventory 是否漂移")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    root = args.root.resolve()
    output = args.output or root / "docs" / "dependency-inventory.json"
    try:
        if args.check:
            if inventory_matches(root, output):
                print("dependency inventory 当前一致")
                return 0
            print(f"dependency inventory 漂移：{output}", file=sys.stderr)
            return 1
        write_inventory(root, output)
    except ValueError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
