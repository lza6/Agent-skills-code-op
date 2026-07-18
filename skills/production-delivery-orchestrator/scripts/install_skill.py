#!/usr/bin/env python3
"""将技能安装到常见智能体目录，并按需生成轻量项目规则桥接。"""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--scope", choices=("user", "project"), default=None)
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
        default=None,
        help="需要写入的原生技能发现目录。",
    )
    parser.add_argument(
        "--bridges",
        nargs="+",
        choices=(*BRIDGE_TARGETS, "all"),
        default=None,
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
    parser.add_argument(
        "--recover",
        action="store_true",
        help=(
            "恢复上一次异常中断且遗留 journal 的安装事务，不执行新的安装；"
            "必须显式重复原安装的 --scope 和 --targets，桥接参数也必须重复。"
        ),
    )
    args = parser.parse_args()
    args.scope_explicit = args.scope is not None
    args.targets_explicit = args.targets is not None
    args.bridges_explicit = args.bridges is not None
    if args.scope is None:
        args.scope = "project"
    if args.targets is None:
        args.targets = ["all"]
    if args.bridges is None:
        args.bridges = []
    return args


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


class InstallTransaction:
    """跨多个技能目录和桥接文件的可补偿安装事务。"""

    JOURNAL_FILE = f".{SKILL_NAME}.install-transaction.json"
    BACKUP_DIR = f".{SKILL_NAME}.install-transaction"

    def __init__(self, anchor: Path) -> None:
        self.anchor = anchor.expanduser().resolve(strict=False)
        self.journal_path = self.anchor / self.JOURNAL_FILE
        self.backup_root = self.anchor / self.BACKUP_DIR
        self.records: list[dict[str, str | bool | None]] = []
        self.transient_paths: list[Path] = []
        self.created_directories: list[Path] = []
        self.anchor_created = False
        self.state = "prepared"
        self.started = False

    def begin(self) -> None:
        if self.journal_path.exists() or self.journal_path.is_symlink():
            raise RuntimeError(
                f"检测到未完成的安装事务：{self.journal_path}；"
                "请先使用 --recover 恢复。"
            )
        if self.backup_root.exists() or self.backup_root.is_symlink():
            raise RuntimeError(
                f"检测到未清理的事务备份目录：{self.backup_root}；"
                "请先人工核对后清理。"
            )

        try:
            if not self.anchor.exists():
                self.anchor.mkdir(parents=True)
                self.anchor_created = True
            self.backup_root.mkdir()
            self._write_journal("prepared")
            self.started = True
        except Exception:
            if self.journal_path.exists() and not self.journal_path.is_symlink():
                self.journal_path.unlink()
            if self.backup_root.exists() and not self.backup_root.is_symlink():
                shutil.rmtree(self.backup_root)
            if self.anchor_created and self.anchor.exists():
                try:
                    self.anchor.rmdir()
                except OSError:
                    pass
            raise

    def snapshot(self, path: Path, kind: str) -> None:
        path = self._safe_anchor_path(path, "事务快照路径")
        if any(record["path"] == str(path) for record in self.records):
            return

        exists = path.exists()
        backup_name: str | None = None
        if exists:
            backup_name = f"backups/{len(self.records):02d}-{kind}"
            backup_path = self.backup_root / backup_name
            if kind == "directory":
                if not path.is_dir() or path.is_symlink():
                    raise ValueError(f"无法备份非普通目录安装目标：{path}")
                shutil.copytree(path, backup_path)
            elif kind == "file":
                if not path.is_file() or path.is_symlink():
                    raise ValueError(f"无法备份非普通文件桥接目标：{path}")
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup_path)
            else:
                raise ValueError(f"未知事务快照类型：{kind}")

        self.records.append(
            {
                "path": str(path),
                "kind": kind,
                "exists": exists,
                "backup": backup_name,
            }
        )
        self._write_journal("prepared")

    def mark_applying(self) -> None:
        self._write_journal("applying")

    def track_transient(self, path: Path) -> None:
        self.transient_paths.append(path)

    def ensure_parent(self, path: Path) -> None:
        missing: list[Path] = []
        current = path.parent
        while not current.exists():
            missing.append(current)
            current = current.parent
        for directory in reversed(missing):
            directory.mkdir()
            self.created_directories.append(directory)
        if missing:
            self._write_journal(self.state)

    def commit(self) -> None:
        self._cleanup_transients()
        self._write_journal("committed")
        shutil.rmtree(self.backup_root)
        self.journal_path.unlink()

    def rollback(self) -> None:
        if not self.started:
            return
        errors: list[Exception] = []
        for record in reversed(self.records):
            try:
                self._restore(record)
            except Exception as error:  # pragma: no cover - 极端 I/O 故障需保留 journal。
                errors.append(error)

        self._cleanup_transients()
        self._cleanup_created_directories()
        if errors:
            self._write_journal("rollback-failed")
            joined = "; ".join(str(error) for error in errors)
            raise RuntimeError(f"安装回滚不完整，已保留 journal：{joined}")

        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        if self.journal_path.exists():
            self.journal_path.unlink()
        if self.anchor_created and self.anchor.exists():
            try:
                self.anchor.rmdir()
            except OSError:
                pass

    def discard_committed(self) -> None:
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root)
        if self.journal_path.exists():
            self.journal_path.unlink()

    def _restore(self, record: dict[str, str | bool | None]) -> None:
        path = self._safe_anchor_path(Path(str(record["path"])), "事务恢复路径")
        kind = str(record["kind"])
        existed = bool(record["exists"])
        if path.exists() or path.is_symlink():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()

        if not existed:
            return

        backup_name = record["backup"]
        if not isinstance(backup_name, str):
            raise RuntimeError(f"事务记录缺少备份：{path}")
        backup_path = self.backup_root / backup_name
        self.ensure_parent(path)
        if kind == "directory":
            shutil.copytree(backup_path, path)
        elif kind == "file":
            shutil.copy2(backup_path, path)
        else:
            raise RuntimeError(f"事务记录类型无效：{kind}")

    def _cleanup_transients(self) -> None:
        for path in reversed(self.transient_paths):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists() or path.is_symlink():
                try:
                    path.unlink()
                except OSError:
                    pass

    def _cleanup_created_directories(self) -> None:
        for directory in reversed(self.created_directories):
            try:
                self._safe_anchor_path(directory, "事务创建目录").rmdir()
            except OSError:
                pass

    def _write_journal(self, state: str) -> None:
        payload = {
            "schema": 1,
            "skill": SKILL_NAME,
            "state": state,
            "backup_dir": str(self.backup_root),
            "records": self.records,
            "created_directories": [str(path) for path in self.created_directories],
        }
        temporary = self.journal_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(self.journal_path)
        self.state = state

    def _safe_anchor_path(self, path: Path, label: str) -> Path:
        if not path.is_absolute():
            raise RuntimeError(f"{label}必须是绝对路径：{path}")
        candidate = path.absolute()
        normalized = candidate.resolve(strict=False)
        try:
            relative = normalized.relative_to(self.anchor)
        except ValueError as error:
            raise RuntimeError(f"{label}越出事务根目录：{path}") from error
        if not relative.parts or ".." in relative.parts:
            raise RuntimeError(f"{label}无效：{path}")
        current = self.anchor
        if current.is_symlink():
            raise RuntimeError(f"事务根目录不能是符号链接：{current}")
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise RuntimeError(f"{label}不能经过符号链接：{path}")
        return current

    def validate_recovery_records(
        self,
        records: object,
        authorized_paths: dict[str, str],
    ) -> list[dict[str, str | bool | None]]:
        if not isinstance(records, list):
            raise RuntimeError(f"事务 journal 缺少 records：{self.journal_path}")
        validated: list[dict[str, str | bool | None]] = []
        seen_paths: set[str] = set()
        for index, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != {
                "path",
                "kind",
                "exists",
                "backup",
            }:
                raise RuntimeError(f"事务 journal 的第 {index} 条 records 无效")
            path_value = record["path"]
            kind = record["kind"]
            existed = record["exists"]
            backup_name = record["backup"]
            if not isinstance(path_value, str) or kind not in {"directory", "file"}:
                raise RuntimeError(f"事务 journal 的第 {index} 条 records 类型无效")
            if type(existed) is not bool:
                raise RuntimeError(f"事务 journal 的第 {index} 条 exists 无效")
            path = self._safe_anchor_path(Path(path_value), "事务 journal 路径")
            if str(path) in seen_paths:
                raise RuntimeError(f"事务 journal 包含重复路径：{path}")
            seen_paths.add(str(path))
            expected_kind = authorized_paths.get(str(path))
            if expected_kind is None or expected_kind != kind:
                raise RuntimeError(f"事务 journal 路径不属于本次恢复计划：{path}")
            expected_backup = f"backups/{index:02d}-{kind}"
            if existed:
                if backup_name != expected_backup:
                    raise RuntimeError(f"事务 journal 的备份名无效：{path}")
                backup_path = self._safe_backup_path(expected_backup)
                if not backup_path.exists():
                    raise RuntimeError(f"事务备份不存在或不安全：{backup_path}")
                if kind == "directory" and not backup_path.is_dir():
                    raise RuntimeError(f"事务目录备份无效：{backup_path}")
                if kind == "file" and not backup_path.is_file():
                    raise RuntimeError(f"事务文件备份无效：{backup_path}")
            elif backup_name is not None:
                raise RuntimeError(f"不存在的原路径不能拥有备份：{path}")
            validated.append(
                {
                    "path": str(path),
                    "kind": kind,
                    "exists": existed,
                    "backup": backup_name,
                }
            )
        return validated

    def _safe_backup_path(self, relative_path: str) -> Path:
        candidate = self.backup_root / relative_path
        try:
            relative = candidate.relative_to(self.backup_root)
        except ValueError as error:  # pragma: no cover - 固定内部路径不会触发。
            raise RuntimeError(f"事务备份路径越界：{candidate}") from error
        current = self.backup_root
        if current.is_symlink():
            raise RuntimeError(f"事务备份目录不能是符号链接：{current}")
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise RuntimeError(f"事务备份路径不能经过符号链接：{candidate}")
        return candidate


def transaction_anchor(scope: str, project_dir: Path) -> Path:
    return Path.home() if scope == "user" else project_dir


def recover_transaction(
    anchor: Path,
    recovery_plan: tuple[tuple[Path, str], ...],
) -> None:
    transaction = InstallTransaction(anchor)
    if transaction.journal_path.is_symlink() or not transaction.journal_path.is_file():
        raise RuntimeError(f"没有可恢复的安装事务：{transaction.journal_path}")
    payload = json.loads(transaction.journal_path.read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or payload.get("skill") != SKILL_NAME:
        raise RuntimeError(f"不支持的事务 journal：{transaction.journal_path}")
    if Path(str(payload.get("backup_dir"))).expanduser().absolute() != transaction.backup_root.absolute():
        raise RuntimeError(f"事务 journal 的备份目录不匹配：{transaction.journal_path}")
    state = payload.get("state")
    if state not in {"prepared", "applying", "rollback-failed", "committed"}:
        raise RuntimeError(f"事务 journal 状态无效：{transaction.journal_path}")
    if state == "committed":
        if transaction.backup_root.is_symlink():
            raise RuntimeError(f"事务备份目录不能是符号链接：{transaction.backup_root}")
        transaction.discard_committed()
        return
    if transaction.backup_root.is_symlink() or not transaction.backup_root.is_dir():
        raise RuntimeError(f"事务备份目录不存在或不安全：{transaction.backup_root}")
    authorized_plan = [
        (transaction._safe_anchor_path(path, "恢复计划路径"), kind)
        for path, kind in recovery_plan
    ]
    authorized_paths = {str(path): kind for path, kind in authorized_plan}
    transaction.records = transaction.validate_recovery_records(
        payload.get("records"), authorized_paths
    )
    created_directories = payload.get("created_directories", [])
    if not isinstance(created_directories, list) or not all(
        isinstance(path, str) for path in created_directories
    ):
        raise RuntimeError(f"事务 journal 的创建目录记录无效：{transaction.journal_path}")
    transaction.created_directories = [
        transaction._safe_anchor_path(Path(path), "事务 journal 创建目录")
        for path in created_directories
    ]
    for directory in transaction.created_directories:
        if not any(
            path != directory and path.is_relative_to(directory)
            for path, _ in authorized_plan
        ):
            raise RuntimeError(f"事务 journal 创建目录不属于本次恢复计划：{directory}")
    transaction.state = state
    transaction.started = True
    transaction.rollback()


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


def copy_skill_transaction(
    source: Path,
    destination: Path,
    transaction: InstallTransaction,
) -> None:
    source = source.resolve()
    destination = destination.expanduser().absolute()
    if source == destination.resolve(strict=False):
        print(f"跳过：当前已从目标目录运行 {destination}")
        return

    action = "替换" if destination.exists() else "安装"
    print(f"{action} {destination}")
    transaction.ensure_parent(destination)
    staging = destination.parent / f".{SKILL_NAME}.staging-{uuid.uuid4().hex}"
    replaced = destination.parent / f".{SKILL_NAME}.replaced-{uuid.uuid4().hex}"
    transaction.track_transient(staging)
    transaction.track_transient(replaced)
    shutil.copytree(
        source,
        staging,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    try:
        if destination.exists():
            destination.rename(replaced)
        staging.rename(destination)
    except Exception:
        if destination.exists() and replaced.exists():
            shutil.rmtree(destination)
        if replaced.exists() and not destination.exists():
            replaced.rename(destination)
        raise


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
对模糊的修复请求，先有边界地侦察仓库和用户旅程，再决定是否需要提问。
明确要求“修复、实现或落地”时，可以完成范围内的本地修改和
非破坏性验证；验证失败时继续在当前范围诊断、修复并复验，除非遇到
不可替代的外部条件。分析、审查或规划请求不得自动修改代码。生产部署、
外部写入、真实付费调用、推送合并、破坏性操作和实质性扩展范围
仍需明确授权。这些项目指令低于平台规则和用户当前授权。
{END_MARKER}"""


def update_managed_file(path: Path, preamble: str, dry_run: bool) -> None:
    updated = updated_managed_file_content(path, preamble)
    print(f"桥接 {path}")
    if dry_run:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    try:
        temporary.write_text(updated, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def update_managed_file_transaction(
    path: Path,
    preamble: str,
    transaction: InstallTransaction,
) -> None:
    updated = updated_managed_file_content(path, preamble)
    print(f"桥接 {path}")
    transaction.ensure_parent(path)
    temporary = path.parent / f".{path.name}.staging-{uuid.uuid4().hex}"
    transaction.track_transient(temporary)
    temporary.write_text(updated, encoding="utf-8", newline="\n")
    temporary.replace(path)


def updated_managed_file_content(path: Path, preamble: str) -> str:
    block = managed_block()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    span = managed_block_span(path, existing)
    if span is not None:
        start, end = span
        updated = existing[:start] + block + existing[end:]
    else:
        prefix = existing.rstrip()
        if not prefix and preamble:
            prefix = preamble.rstrip()
        updated = f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"
    return updated


def managed_block_span(path: Path, existing: str) -> tuple[int, int] | None:
    start_count = existing.count(START_MARKER)
    end_count = existing.count(END_MARKER)
    if start_count == 0 and end_count == 0:
        return None
    if start_count != 1 or end_count != 1:
        raise RuntimeError(f"{path} 中的受管标记格式错误")

    start = existing.index(START_MARKER)
    end_start = existing.index(END_MARKER)
    if start >= end_start:
        raise RuntimeError(f"{path} 中的受管标记格式错误：结束标记必须位于开始标记之后")
    return start, end_start + len(END_MARKER)


def preflight_managed_file(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"拒绝更新符号链接桥接目标：{path}")
    if not path.exists():
        return
    if not path.is_file():
        raise ValueError(f"桥接目标存在但不是普通文件：{path}")
    existing = path.read_text(encoding="utf-8")
    managed_block_span(path, existing)


def bridge_specs() -> dict[str, tuple[Path, str]]:
    cursor_preamble = """---
description: 对软件任务应用生产级交付编排器
globs:
alwaysApply: true
---"""
    return {
        "agents-md": (Path("AGENTS.md"), ""),
        "claude-md": (Path("CLAUDE.md"), ""),
        "gemini-md": (Path("GEMINI.md"), ""),
        "copilot": (Path(".github") / "copilot-instructions.md", ""),
        "cursor": (
            Path(".cursor") / "rules" / f"{SKILL_NAME}.mdc",
            cursor_preamble,
        ),
        "windsurf": (
            Path(".windsurf") / "rules" / f"{SKILL_NAME}.md",
            "",
        ),
        "cline": (
            Path(".clinerules") / f"{SKILL_NAME}.md",
            "",
        ),
    }


def resolve_project_path(project_dir: Path, value: Path, kind: str) -> Path:
    if value.is_absolute():
        raise ValueError(f"{kind}必须使用项目相对路径，当前为：{value}")
    project_dir = project_dir.resolve(strict=False)
    requested = project_dir / value
    if requested.is_symlink():
        raise ValueError(f"{kind}不能指向符号链接，且不得越出了项目目录：{value}")
    resolved = requested.resolve(strict=False)
    try:
        resolved.relative_to(project_dir)
    except ValueError as exc:
        raise ValueError(f"{kind}越出了项目目录：{value}") from exc
    return resolved


def resolve_bridge(project_dir: Path, value: Path) -> Path:
    return resolve_project_path(project_dir, value, "桥接")


def resolve_install_plan(
    args: argparse.Namespace,
    project_dir: Path,
) -> tuple[list[Path], tuple[tuple[Path, str], ...]]:
    targets = expand(args.targets, NATIVE_TARGETS)
    bridges = expand(args.bridges, BRIDGE_TARGETS)
    if (bridges or args.custom_bridge) and args.scope != "project":
        raise ValueError("指令桥接只支持项目级安装；请使用 --scope project。")
    if (bridges or args.custom_bridge) and "agents" not in targets:
        targets.append("agents")

    destinations: list[Path] = []
    for target in targets:
        destination = target_base(args.scope, target, project_dir) / SKILL_NAME
        if args.scope == "project":
            relative_destination = destination.relative_to(project_dir)
            destination = resolve_project_path(
                project_dir, relative_destination, "安装目标"
            )
        destinations.append(destination)

    specs = bridge_specs()
    selected_bridges = [
        (resolve_bridge(project_dir, specs[bridge][0]), specs[bridge][1])
        for bridge in bridges
    ]
    custom_bridges = [
        (resolve_bridge(project_dir, value), "") for value in args.custom_bridge
    ]
    return destinations, tuple((*selected_bridges, *custom_bridges))


def configure_console_utf8() -> None:
    """Prefer readable UTF-8 diagnostics without requiring configurable streams."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, TypeError, ValueError):
            # Embedded or already-detached streams can reject reconfiguration.
            continue


def main() -> int:
    configure_console_utf8()
    args = parse_args()
    project_dir = args.project_dir.expanduser().resolve()
    destinations, bridge_paths = resolve_install_plan(args, project_dir)
    if args.recover:
        if not args.scope_explicit or not args.targets_explicit:
            raise ValueError(
                "--recover 必须显式提供原安装的 --scope 和 --targets；"
                "如果原安装使用桥接，也必须重复提供 --bridges 和 --custom-bridge。"
            )
        recovery_plan = tuple(
            [(destination, "directory") for destination in destinations]
            + [(path, "file") for path, _ in bridge_paths]
        )
        recover_transaction(transaction_anchor(args.scope, project_dir), recovery_plan)
        print("完成：已恢复上一次未完成的安装事务")
        return 0

    source = source_root()

    for destination in destinations:
        preflight_destination(source, destination, args.force)
    for path, _ in bridge_paths:
        preflight_managed_file(path)

    if args.dry_run:
        for destination in destinations:
            copy_skill(source, destination, args.force, dry_run=True)
        for path, preamble in bridge_paths:
            update_managed_file(path, preamble, dry_run=True)
        print("完成：演练模式，未写入")
        return 0

    transaction = InstallTransaction(transaction_anchor(args.scope, project_dir))
    try:
        transaction.begin()
        for destination in destinations:
            if source != destination.expanduser().resolve(strict=False):
                transaction.snapshot(destination, "directory")
        for path, _ in bridge_paths:
            transaction.snapshot(path, "file")

        transaction.mark_applying()
        for destination in destinations:
            copy_skill_transaction(source, destination, transaction)
        for path, preamble in bridge_paths:
            update_managed_file_transaction(path, preamble, transaction)
    except BaseException:
        try:
            transaction.rollback()
        except Exception as rollback_error:
            print(f"错误：{rollback_error}", file=sys.stderr)
        raise
    else:
        transaction.commit()

    print("完成")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
