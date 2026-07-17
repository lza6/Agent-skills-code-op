#!/usr/bin/env python3
"""Optional, bounded repository inventory for production-delivery-orchestrator.

The scanner deliberately inspects filenames only. It is an aid for initial
reconnaissance, not a build system, code parser, or mandatory skill dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


DEFAULT_MAX_FILES = 12_000
MAX_SAMPLES = 40
IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".next",
        ".nuxt",
        ".turbo",
        ".venv",
        "__pycache__",
        "bower_components",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "target",
        "vendor",
        "venv",
    }
)
LANGUAGE_SUFFIXES = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".dart": "Dart",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".scala": "Scala",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
}
FILE_SIGNALS = {
    "Cargo.toml": "Rust/Cargo",
    "Dockerfile": "Docker",
    "Gemfile": "Ruby/Bundler",
    "Makefile": "Make",
    "Package.swift": "Swift Package Manager",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "composer.json": "PHP/Composer",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "go.mod": "Go modules",
    "package.json": "Node.js package",
    "pnpm-lock.yaml": "pnpm",
    "pom.xml": "Maven",
    "pyproject.toml": "Python project",
    "requirements.txt": "Python requirements",
    "setup.py": "Python setuptools",
    "uv.lock": "uv",
    "yarn.lock": "Yarn",
}
ENTRY_NAMES = frozenset(
    {
        "app.py",
        "index.js",
        "index.ts",
        "main.go",
        "main.py",
        "main.rs",
        "manage.py",
        "server.js",
        "server.ts",
        "wsgi.py",
    }
)


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def iter_repository_files(root: Path, max_files: int) -> tuple[Iterator[Path], dict[str, bool]]:
    """Yield regular non-symlink files in deterministic order without leaving root."""

    state = {"truncated": False}

    def files() -> Iterator[Path]:
        yielded = 0
        for directory, directory_names, file_names in os.walk(root, topdown=True):
            current = Path(directory)
            kept_directories: list[str] = []
            for name in sorted(directory_names):
                candidate = current / name
                if name in IGNORED_DIRECTORIES or candidate.is_symlink():
                    continue
                kept_directories.append(name)
            directory_names[:] = kept_directories

            for name in sorted(file_names):
                candidate = current / name
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                if yielded >= max_files:
                    state["truncated"] = True
                    return
                yielded += 1
                yield candidate

    return files(), state


def append_sample(samples: list[str], path: str) -> None:
    if len(samples) < MAX_SAMPLES:
        samples.append(path)


def looks_like_test(relative_path: str) -> bool:
    parts = relative_path.lower().split("/")
    name = parts[-1]
    return (
        "test" in parts
        or "tests" in parts
        or name.startswith("test_")
        or name.endswith((".test.js", ".test.ts", ".test.tsx", ".spec.js", ".spec.ts", ".spec.tsx"))
    )


def inventory(root: Path, max_files: int = DEFAULT_MAX_FILES) -> dict[str, Any]:
    """Return a portable filename-only inventory for a bounded repository tree."""

    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"仓库根目录不存在或不是目录：{root}")
    if max_files < 1:
        raise ValueError("max_files 必须至少为 1")

    language_counts: Counter[str] = Counter()
    signals: list[dict[str, str]] = []
    entry_candidates: list[str] = []
    test_candidates: list[str] = []
    files, state = iter_repository_files(resolved_root, max_files)
    files_scanned = 0

    for path in files:
        relative = path.relative_to(resolved_root).as_posix()
        files_scanned += 1
        language = LANGUAGE_SUFFIXES.get(path.suffix.lower())
        if language:
            language_counts[language] += 1
        signal = FILE_SIGNALS.get(path.name)
        if signal:
            signals.append({"path": relative, "signal": signal})
        if path.name in ENTRY_NAMES:
            append_sample(entry_candidates, relative)
        if looks_like_test(relative):
            append_sample(test_candidates, relative)

    return {
        "schema": 1,
        "kind": "optional_repository_inventory",
        "scope": "filename-only, bounded, no source parsing or execution",
        "files_scanned": files_scanned,
        "truncated": state["truncated"],
        "max_files": max_files,
        "ignored_directories": sorted(IGNORED_DIRECTORIES),
        "languages": dict(sorted(language_counts.items())),
        "signals": sorted(signals, key=lambda item: (item["path"], item["signal"])),
        "entry_candidates": entry_candidates,
        "test_candidates": test_candidates,
        "sample_limit": MAX_SAMPLES,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成可选、受限的代码库文件名盘点 JSON。")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="仓库根目录")
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"最多扫描的常规文件数（默认 {DEFAULT_MAX_FILES}）",
    )
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    try:
        report = inventory(args.root, args.max_files)
    except ValueError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
