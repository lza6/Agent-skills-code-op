#!/usr/bin/env python3
"""Build and query the repository's lightweight skill registry manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
FRONTMATTER_FIELD_PATTERN = re.compile(r"(?P<key>[a-z][a-z0-9_-]*): (?P<value>\S(?:.*\S)?)\Z")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def parse_frontmatter(skill_path: Path) -> dict[str, str]:
    """Return strict scalar frontmatter fields from a SKILL.md file."""

    try:
        lines = skill_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError(f"{skill_path}: frontmatter 必须是 UTF-8") from error

    if not lines or lines[0] != "---":
        raise ValueError(f"{skill_path}: 缺少 frontmatter 起始分隔符")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as error:
        raise ValueError(f"{skill_path}: 缺少 frontmatter 结束分隔符") from error

    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:closing_index], start=2):
        match = FRONTMATTER_FIELD_PATTERN.fullmatch(line)
        if match is None:
            raise ValueError(f"{skill_path}:{line_number}: 非法 frontmatter 字段")
        key = match["key"]
        if key in fields:
            raise ValueError(f"{skill_path}:{line_number}: frontmatter 字段重复：{key}")
        fields[key] = match["value"]

    name = fields.get("name")
    if name is None or not NAME_PATTERN.fullmatch(name):
        raise ValueError(f"{skill_path}: frontmatter name 必须是小写连字符标识符")
    if not fields.get("description"):
        raise ValueError(f"{skill_path}: frontmatter 缺少非空 description")
    return fields


def discover_skill_paths(root: Path) -> list[Path]:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(
        (
            path
            for path in skills_root.rglob("SKILL.md")
            if path.is_file() and not path.is_symlink()
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def build_registry(root: Path) -> dict[str, Any]:
    """Discover skills below ``root`` and return a deterministic registry."""

    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"仓库根目录不存在或不是目录：{root}")

    entries: list[dict[str, str]] = []
    seen_names: dict[str, str] = {}
    for skill_path in discover_skill_paths(resolved_root):
        fields = parse_frontmatter(skill_path)
        name = fields["name"]
        relative_path = skill_path.relative_to(resolved_root).as_posix()
        if name in seen_names:
            raise ValueError(
                f"技能 name 重复：{name}（{seen_names[name]} 与 {relative_path}）"
            )
        seen_names[name] = relative_path
        entries.append(
            {
                "description": fields["description"],
                "name": name,
                "path": relative_path,
            }
        )

    return {"schema": SCHEMA_VERSION, "skills": sorted(entries, key=lambda item: item["name"])}


def registry_json(registry: dict[str, Any]) -> str:
    return json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_registry(root: Path, output: Path) -> dict[str, Any]:
    registry = build_registry(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(registry_json(registry), encoding="utf-8", newline="\n")
    return registry


def registry_matches(root: Path, output: Path) -> bool:
    try:
        actual = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return actual == build_registry(root)


def tokenize(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_PATTERN.findall(value)}


def query_registry(registry: dict[str, Any], query: str) -> list[dict[str, str]]:
    """Return name-sorted entries sharing at least one query token."""

    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    return [
        entry
        for entry in registry["skills"]
        if query_tokens
        & tokenize(f"{entry['name']} {entry['description']}")
    ]


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成或查询单技能 registry manifest。")
    parser.add_argument("--root", type=Path, default=default_root(), help="仓库根目录")
    parser.add_argument("--output", type=Path, help="registry 输出路径（默认 skills/registry.json）")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只检查已生成 manifest 是否漂移")
    mode.add_argument("--query", help="返回名称或描述词元相交的稳定条目")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    root = args.root.resolve()
    output = args.output or root / "skills" / "registry.json"
    try:
        if args.query is not None:
            registry = build_registry(root)
            report = {
                "query": args.query,
                "schema": SCHEMA_VERSION,
                "skills": query_registry(registry, args.query),
            }
            print(registry_json(report), end="")
            return 0
        if args.check:
            if registry_matches(root, output):
                print("skill registry manifest 当前一致")
                return 0
            print(f"skill registry manifest 漂移：{output}", file=sys.stderr)
            return 1
        write_registry(root, output)
    except ValueError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
