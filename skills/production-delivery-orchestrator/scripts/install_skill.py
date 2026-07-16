#!/usr/bin/env python3
"""将技能安装到常见智能体目录，并按需生成轻量项目规则桥接。"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import uuid
from pathlib import Path


SKILL_NAME = "production-delivery-orchestrator"
START_MARKER = "<!-- production-delivery-orchestrator:start -->"
END_MARKER = "<!-- production-delivery-orchestrator:end -->"

NATIVE_TARGETS = ("codex", "claude", "agents")
BRIDGE_TARGETS = (
    "agents-md",
    "claude-md",
    "gemini-md",
    "copilot",
    "cursor",
    "windsurf",
    "cline",
)
REFERENCE_LINK_RE = re.compile(r"`(references/[A-Za-z0-9_.\-/]+\.md)`")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "将通用技能安装到 Codex、Claude Code 和通用 Agent Skills 目录；"
            "也可为其他编码智能体生成只负责能力路由的项目指令桥接。"
        )
    )
    parser.add_argument("--scope", choices=("user", "project"), default="project")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="项目级安装的仓库根目录（默认为当前目录）。",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=(*NATIVE_TARGETS, "all"),
        default=["all"],
        help="需要写入的原生技能发现目录。",
    )
    parser.add_argument(
        "--bridges",
        nargs="+",
        choices=(*BRIDGE_TARGETS, "all"),
        default=[],
        help="需要创建或更新的项目指令文件或规则。",
    )
    parser.add_argument(
        "--custom-bridge",
        action="append",
        type=Path,
        default=[],
        help=(
            "要桥接的其他项目相对路径指令文件。多个工具可重复传入，"
            "例如 --custom-bridge .tool/rules.md。"
        ),
    )
    parser.add_argument("--force", action="store_true", help="替换已存在的安装副本。")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划变更，不写入文件。")
    return parser.parse_args()


def expand(values: list[str], universe: tuple[str, ...]) -> list[str]:
    if "all" in values:
        return list(universe)
    return list(dict.fromkeys(values))


def source_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    skill_md = root / "SKILL.md"
    required = [skill_md, root / "agents" / "openai.yaml"]
    if skill_md.is_file():
        links = dict.fromkeys(REFERENCE_LINK_RE.findall(skill_md.read_text(encoding="utf-8")))
        required.extend(root / Path(link) for link in links)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"技能源文件不完整，缺少：{', '.join(missing)}")
    return root


def target_base(scope: str, target: str, project_dir: Path) -> Path:
    if scope == "user":
        bases = {
            "codex": Path.home() / ".codex" / "skills",
            "claude": Path.home() / ".claude" / "skills",
            "agents": Path.home() / ".agents" / "skills",
        }
    else:
        bases = {
            "codex": project_dir / ".codex" / "skills",
            "claude": project_dir / ".claude" / "skills",
            "agents": project_dir / ".agents" / "skills",
        }
    return bases[target]


def copy_skill(source: Path, destination: Path, force: bool, dry_run: bool) -> None:
    source = source.resolve()
    destination = destination.expanduser().absolute()

    if destination.is_symlink():
        raise ValueError(f"拒绝替换符号链接目标：{destination}")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"安装目标存在但不是目录：{destination}")

    if source == destination.resolve(strict=False):
        print(f"跳过：当前已从目标目录运行 {destination}")
        return

    if destination.exists() and not force:
        raise FileExistsError(
            f"{destination} 已存在；只有在确认要替换时才使用 --force 重新运行。"
        )

    action = "替换" if destination.exists() else "安装"
    print(f"{action} {destination}")
    if dry_run:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{SKILL_NAME}.staging-{uuid.uuid4().hex}"
    shutil.copytree(
        source,
        staging,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    backup: Path | None = None
    try:
        if destination.exists():
            backup = destination.parent / f".{SKILL_NAME}.backup-{uuid.uuid4().hex}"
            destination.rename(backup)
        staging.rename(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if backup is not None and backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    else:
        if backup is not None and backup.exists():
            shutil.rmtree(backup)


def preflight_destination(source: Path, destination: Path, force: bool) -> None:
    source = source.resolve()
    destination = destination.expanduser().absolute()
    if destination.is_symlink():
        raise ValueError(f"拒绝安装到符号链接目标：{destination}")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"安装目标存在但不是目录：{destination}")
    if source != destination.resolve(strict=False) and destination.exists() and not force:
        raise FileExistsError(
            f"{destination} 已存在；只有在确认要替换时才使用 --force 重新运行。"
        )


def managed_block() -> str:
    return f"""{START_MARKER}
## 生产级交付编排器

当用户明确调用 `{SKILL_NAME}`，或请求端到端的软件实现、修复、
重构、复杂审查、生产级验证，或只描述了需要从仓库侦察的模糊故障时，
读取并应用 `.agents/skills/{SKILL_NAME}/SKILL.md`。

该技能采用渐进披露：先读取 `SKILL.md`，再只按其中的任务路由读取
与当前请求直接相关的 reference。不要默认全文加载所有 reference，
也不要把 `references/system-prompt.md` 作为每个软件请求的强制前置。
纯事实问答、非软件请求和无需生产交付闭环的简单任务不必启用本技能。

执行其结果门：如果用户最终可见的结果存在实质性歧义，
提供两到三个以结果为导向的选项，并将推荐结果放在第一个。
不要要求用户选择可以从仓库事实中推导的底层实现细节。
明确要求“修复、实现或落地”时，可以完成范围内的本地修改和
非破坏性验证；分析、审查或规划请求不得自动修改代码。生产部署、
外部写入、真实付费调用、推送合并、破坏性操作和实质性扩展范围
仍需明确授权。这些项目指令低于平台规则和用户当前授权。
{END_MARKER}"""


def update_managed_file(path: Path, preamble: str, dry_run: bool) -> None:
    block = managed_block()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    if START_MARKER in existing or END_MARKER in existing:
        if existing.count(START_MARKER) != 1 or existing.count(END_MARKER) != 1:
            raise RuntimeError(f"{path} 中的受管标记格式错误")
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER, start) + len(END_MARKER)
        updated = existing[:start] + block + existing[end:]
    else:
        prefix = existing.rstrip()
        if not prefix and preamble:
            prefix = preamble.rstrip()
        updated = f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"

    print(f"桥接 {path}")
    if dry_run:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8", newline="\n")


def preflight_managed_file(path: Path) -> None:
    if not path.exists():
        return
    existing = path.read_text(encoding="utf-8")
    if START_MARKER in existing or END_MARKER in existing:
        if existing.count(START_MARKER) != 1 or existing.count(END_MARKER) != 1:
            raise RuntimeError(f"{path} 中的受管标记格式错误")


def bridge_specs(project_dir: Path) -> dict[str, tuple[Path, str]]:
    cursor_preamble = """---
description: 对软件任务应用生产级交付编排器
globs:
alwaysApply: true
---"""
    return {
        "agents-md": (project_dir / "AGENTS.md", ""),
        "claude-md": (project_dir / "CLAUDE.md", ""),
        "gemini-md": (project_dir / "GEMINI.md", ""),
        "copilot": (project_dir / ".github" / "copilot-instructions.md", ""),
        "cursor": (
            project_dir / ".cursor" / "rules" / f"{SKILL_NAME}.mdc",
            cursor_preamble,
        ),
        "windsurf": (
            project_dir / ".windsurf" / "rules" / f"{SKILL_NAME}.md",
            "",
        ),
        "cline": (
            project_dir / ".clinerules" / f"{SKILL_NAME}.md",
            "",
        ),
    }


def resolve_custom_bridge(project_dir: Path, value: Path) -> Path:
    if value.is_absolute():
        raise ValueError(f"自定义桥接必须使用项目相对路径，当前为：{value}")
    resolved = (project_dir / value).resolve()
    try:
        resolved.relative_to(project_dir)
    except ValueError as exc:
        raise ValueError(f"自定义桥接越出了项目目录：{value}") from exc
    return resolved


def main() -> int:
    args = parse_args()
    source = source_root()
    project_dir = args.project_dir.expanduser().resolve()
    targets = expand(args.targets, NATIVE_TARGETS)
    bridges = expand(args.bridges, BRIDGE_TARGETS)

    if (bridges or args.custom_bridge) and args.scope != "project":
        raise ValueError("指令桥接只支持项目级安装；请使用 --scope project。")

    if (bridges or args.custom_bridge) and "agents" not in targets:
        targets.append("agents")

    destinations = [
        target_base(args.scope, target, project_dir) / SKILL_NAME for target in targets
    ]
    specs = bridge_specs(project_dir)
    selected_bridges = [specs[bridge] for bridge in bridges]
    custom_bridges = [
        (resolve_custom_bridge(project_dir, value), "") for value in args.custom_bridge
    ]

    for destination in destinations:
        preflight_destination(source, destination, args.force)
    for path, _ in (*selected_bridges, *custom_bridges):
        preflight_managed_file(path)

    for destination in destinations:
        copy_skill(source, destination, args.force, args.dry_run)

    for path, preamble in (*selected_bridges, *custom_bridges):
        update_managed_file(path, preamble, args.dry_run)

    print("完成：演练模式，未写入" if args.dry_run else "完成")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
