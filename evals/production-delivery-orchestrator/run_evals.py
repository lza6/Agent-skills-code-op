#!/usr/bin/env python3
"""Offline evaluation for production-delivery-orchestrator.

This runner intentionally does not call an LLM. It evaluates prompt structure,
rule coverage, trigger-boundary proxies, a small repository fixture, and
completion gates. The generated report must not be presented as proof of real
agent behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
DEFAULT_CANDIDATE = REPO_ROOT / "skills" / "production-delivery-orchestrator"
DEFAULT_FIXTURE = EVAL_DIR / "fixtures" / "video-polling-state-machine"
DEFAULT_BASELINE_GIT_REF = "b3d9a17"
DEFAULT_SKILL_RELATIVE_PATH = "skills/production-delivery-orchestrator"
LEGACY_SYSTEM_PROMPT = "references/system-prompt.md"
REFERENCE_LINK_PATTERN = r"references/[A-Za-z0-9_.\-/]+\.md"
REPORT_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_report_prefix(prefix: str) -> str:
    """Allow only a single portable report filename prefix."""

    if (
        not isinstance(prefix, str)
        or not REPORT_PREFIX_RE.fullmatch(prefix)
        or ".." in prefix
        or "/" in prefix
        or "\\" in prefix
    ):
        raise ValueError(
            "report-prefix 必须是纯安全文件名前缀：以字母或数字开头，"
            "只可包含字母、数字、._-，且不得包含 .. 或路径分隔符"
        )
    return prefix


def _portable_pure_path(path: str | Path) -> PurePosixPath | PureWindowsPath:
    """Parse either Windows or POSIX path syntax without depending on the host OS."""

    text = str(path)
    if re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", text) or "\\" in text:
        return PureWindowsPath(text)
    return PurePosixPath(text)


def _portable_relative_path(
    path: str | Path, root: str | Path
) -> PurePosixPath | PureWindowsPath | None:
    parsed_path = _portable_pure_path(path)
    parsed_root = _portable_pure_path(root)
    if type(parsed_path) is not type(parsed_root):
        return None
    try:
        return parsed_path.relative_to(parsed_root)
    except ValueError:
        return None


def display_path(
    path: str | Path,
    *,
    repo_root: str | Path = REPO_ROOT,
    external_label: str = "path",
    external_root: str | Path | None = None,
) -> str:
    """Return a deterministic report path without exposing the host filesystem.

    Repository paths are POSIX-style and repository-relative. Git object paths
    already carry a portable source identifier and are preserved. Files outside
    the repository use an explicit, stable ``external:<label>`` namespace; when
    an external root is supplied, only the path relative to that root is shown.
    """

    text = str(path)
    if text.startswith("git:"):
        return text

    repo_relative = _portable_relative_path(text, repo_root)
    if repo_relative is not None:
        return repo_relative.as_posix()

    parsed = _portable_pure_path(text)
    if not parsed.is_absolute() and ".." not in parsed.parts:
        return parsed.as_posix()

    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", external_label).strip("-.")
    prefix = f"external:{safe_label or 'path'}"
    if external_root is not None:
        external_relative = _portable_relative_path(text, external_root)
        if external_relative is not None and external_relative.parts:
            return f"{prefix}/{external_relative.as_posix()}"
    return prefix


@dataclass
class Artifact:
    label: str
    source: str
    core_path: str
    core_text: str
    all_text: str
    capability_text: str
    frontmatter: dict[str, str]
    reference_paths: list[str]
    routed_reference_paths: list[str]
    forced_legacy_reference_paths: list[str]
    legacy_excluded_reference_paths: list[str]
    default_context_chars: int
    tree_sha256: str


@dataclass
class CheckResult:
    id: str
    title: str
    passed: bool
    critical: bool
    weight: int
    evidence: list[str]


def load_json_yaml(path: Path) -> dict[str, Any]:
    """Load rubric.yaml without requiring PyYAML.

    JSON is valid YAML 1.2, so the rubric is deliberately written as JSON.
    """

    return json.loads(path.read_text(encoding="utf-8"))


def parse_cases(path: Path) -> list[dict[str, Any]]:
    """Parse the limited cases.yaml shape using only the standard library."""

    lines = path.read_text(encoding="utf-8").splitlines()
    cases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_list: str | None = None
    index = 0

    while index < len(lines):
        line = lines[index]
        id_match = re.match(r"^  - id:\s*(.+?)\s*$", line)
        if id_match:
            if current:
                cases.append(current)
            current = {"id": id_match.group(1), "must": [], "must_not": []}
            active_list = None
            index += 1
            continue

        if current is None:
            index += 1
            continue

        field_match = re.match(r"^    (prompt|context):\s*(.*)$", line)
        if field_match:
            field, value = field_match.groups()
            active_list = None
            if value in {">-", "|", "|-"}:
                block: list[str] = []
                index += 1
                while index < len(lines) and (
                    not lines[index].strip() or lines[index].startswith("      ")
                ):
                    block.append(lines[index].strip())
                    index += 1
                current[field] = " ".join(part for part in block if part)
                continue
            current[field] = value.strip().strip('"')
            index += 1
            continue

        list_match = re.match(r"^    (must|must_not):\s*$", line)
        if list_match:
            active_list = list_match.group(1)
            index += 1
            continue

        item_match = re.match(r"^      -\s+(.+?)\s*$", line)
        if item_match and active_list:
            current[active_list].append(item_match.group(1))

        index += 1

    if current:
        cases.append(current)
    return cases


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            metadata[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return metadata, parts[2]


def forces_legacy_system_prompt(core_text: str) -> bool:
    unconditional_patterns = (
        r"必须完整读取\s*`?references/system-prompt\.md`?",
        r"始终完整读取[^\n]{0,120}references/system-prompt\.md",
        r"references/system-prompt\.md[^\n]{0,120}不得用摘要替代",
    )
    return any(regex_found(core_text, pattern) for pattern in unconditional_patterns)


def reference_route_key(path: str) -> str:
    normalized = path.replace("\\", "/")
    marker = "references/"
    index = normalized.lower().rfind(marker)
    return normalized[index:].lower() if index >= 0 else normalized.lower()


def select_capability_references(
    core_text: str,
    reference_paths: list[str],
    reference_texts: list[str],
    *,
    allow_forced_legacy_protocol: bool,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return routed modular refs, forced legacy refs, excluded legacy refs, texts.

    Capability reachability follows references explicitly linked from SKILL.md. The
    compatibility system-prompt is never treated as a modular route. It is included
    only for a baseline whose core unconditionally forces that long protocol.
    """

    linked_routes = {
        match.lower() for match in re.findall(REFERENCE_LINK_PATTERN, core_text, re.IGNORECASE)
    }
    routed_paths: list[str] = []
    forced_legacy_paths: list[str] = []
    legacy_excluded_paths: list[str] = []
    capability_reference_texts: list[str] = []
    include_legacy = allow_forced_legacy_protocol and forces_legacy_system_prompt(core_text)

    for path, text in zip(reference_paths, reference_texts):
        route_key = reference_route_key(path)
        if route_key == LEGACY_SYSTEM_PROMPT:
            if include_legacy:
                forced_legacy_paths.append(path)
                capability_reference_texts.append(text)
            else:
                legacy_excluded_paths.append(path)
            continue
        if route_key in linked_routes:
            routed_paths.append(path)
            capability_reference_texts.append(text)

    return (
        routed_paths,
        forced_legacy_paths,
        legacy_excluded_paths,
        capability_reference_texts,
    )


def calculate_default_context_chars(
    core_text: str, forced_legacy_reference_texts: list[str]
) -> int:
    """Estimate the initial forced prompt surface, not eventual on-demand reads."""

    return len(core_text) + sum(map(len, forced_legacy_reference_texts))


def load_artifact(
    path: Path, label: str, *, allow_forced_legacy_protocol: bool = False
) -> Artifact:
    path = path.resolve()
    if path.is_dir():
        core_path = path / "SKILL.md"
        root = path
    else:
        core_path = path
        root = path.parent

    display_root = root

    if not core_path.is_file():
        raise FileNotFoundError(f"{label} 缺少 SKILL.md 或 Markdown 文件：{path}")

    core_text = core_path.read_text(encoding="utf-8")
    frontmatter, _ = split_frontmatter(core_text)
    reference_paths: list[str] = []
    reference_texts: list[str] = []
    references_dir = root / "references"
    if core_path.name == "SKILL.md" and references_dir.is_dir():
        references = sorted(
            references_dir.rglob("*.md"),
            key=lambda reference: reference.relative_to(root).as_posix(),
        )
        for reference in references:
            reference_paths.append(
                display_path(
                    reference,
                    external_label=label,
                    external_root=display_root,
                )
            )
            reference_texts.append(reference.read_text(encoding="utf-8"))

    (
        routed_reference_paths,
        forced_legacy_reference_paths,
        legacy_excluded_reference_paths,
        capability_reference_texts,
    ) = select_capability_references(
        core_text,
        reference_paths,
        reference_texts,
        allow_forced_legacy_protocol=allow_forced_legacy_protocol,
    )
    forced_legacy_texts = [
        text
        for path, text in zip(reference_paths, reference_texts)
        if path in forced_legacy_reference_paths
    ]

    return Artifact(
        label=label,
        source=display_path(
            path,
            external_label=label,
            external_root=display_root,
        ),
        core_path=display_path(
            core_path,
            external_label=label,
            external_root=display_root,
        ),
        core_text=core_text,
        all_text="\n".join([core_text, *reference_texts]),
        capability_text="\n".join([core_text, *capability_reference_texts]),
        frontmatter=frontmatter,
        reference_paths=reference_paths,
        routed_reference_paths=routed_reference_paths,
        forced_legacy_reference_paths=forced_legacy_reference_paths,
        legacy_excluded_reference_paths=legacy_excluded_reference_paths,
        default_context_chars=calculate_default_context_chars(core_text, forced_legacy_texts),
        tree_sha256=sha256_path_tree(path),
    )


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} 执行失败")
    return result.stdout


def run_git_bytes(*args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(message or f"git {' '.join(args)} 执行失败")
    return result.stdout


def preflight_default_git_baseline(ref: str, skill_relative_path: str) -> None:
    """Fail early with a recovery path when the published Git baseline is unavailable."""

    core_path = f"{skill_relative_path.rstrip('/')}/SKILL.md"
    try:
        run_git("rev-parse", "--verify", f"{ref}^{{commit}}")
        run_git("cat-file", "-e", f"{ref}:{core_path}")
    except ValueError as error:
        raise ValueError(
            f"默认 Git baseline `{ref}` 不可用；当前 checkout 可能是 shallow clone 或 "
            "GitHub Source archive。请获取包含该提交的完整历史（例如 `git fetch "
            "--unshallow`），或显式传入 `--baseline <skill-dir-or-SKILL.md>`。"
        ) from error


def load_git_artifact(
    ref: str,
    skill_relative_path: str,
    label: str,
    *,
    allow_forced_legacy_protocol: bool = False,
) -> Artifact:
    """Load the actual published baseline from Git without creating a checkout."""

    core_path = f"{skill_relative_path}/SKILL.md"
    core_text = run_git("show", f"{ref}:{core_path}")
    frontmatter, _ = split_frontmatter(core_text)
    reference_prefix = f"{skill_relative_path}/references"
    names = run_git("ls-tree", "-r", "--name-only", ref, "--", reference_prefix)
    reference_paths = [
        name for name in names.splitlines() if name.endswith(".md")
    ]
    reference_texts = [run_git("show", f"{ref}:{name}") for name in reference_paths]
    (
        routed_reference_paths,
        forced_legacy_reference_paths,
        legacy_excluded_reference_paths,
        capability_reference_texts,
    ) = select_capability_references(
        core_text,
        reference_paths,
        reference_texts,
        allow_forced_legacy_protocol=allow_forced_legacy_protocol,
    )
    forced_legacy_texts = [
        text
        for path, text in zip(reference_paths, reference_texts)
        if path in forced_legacy_reference_paths
    ]
    artifact_names = run_git(
        "ls-tree", "-r", "--name-only", ref, "--", skill_relative_path
    ).splitlines()
    artifact_entries = []
    prefix = f"{skill_relative_path.rstrip('/')}/"
    for name in artifact_names:
        relative_name = name[len(prefix) :] if name.startswith(prefix) else name
        if should_hash_relative_path(relative_name):
            artifact_entries.append(
                (relative_name, run_git_bytes("show", f"{ref}:{name}"))
            )
    return Artifact(
        label=label,
        source=f"git:{ref}:{skill_relative_path}",
        core_path=f"git:{ref}:{core_path}",
        core_text=core_text,
        all_text="\n".join([core_text, *reference_texts]),
        capability_text="\n".join([core_text, *capability_reference_texts]),
        frontmatter=frontmatter,
        reference_paths=reference_paths,
        routed_reference_paths=routed_reference_paths,
        forced_legacy_reference_paths=forced_legacy_reference_paths,
        legacy_excluded_reference_paths=legacy_excluded_reference_paths,
        default_context_chars=calculate_default_context_chars(core_text, forced_legacy_texts),
        tree_sha256=sha256_tree_entries(artifact_entries),
    )


def regex_found(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_tree_content(content: bytes) -> bytes:
    """Normalize UTF-8 text EOLs while preserving binary bytes."""

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def should_hash_relative_path(relative_path: str) -> bool:
    parts = PurePosixPath(relative_path.replace("\\", "/")).parts
    return not (
        relative_path.endswith((".pyc", ".pyo")) or "__pycache__" in parts
    )


def sha256_tree_entries(entries: list[tuple[str, bytes]]) -> str:
    """Hash portable path/content entries independently of host path semantics."""

    digest = hashlib.sha256()
    digest.update(b"production-delivery-eval-tree-v1\0")
    for relative_name, raw_content in sorted(
        entries, key=lambda entry: entry[0].replace("\\", "/")
    ):
        relative_path = relative_name.replace("\\", "/").encode("utf-8")
        content = canonical_tree_content(raw_content)
        digest.update(len(relative_path).to_bytes(8, byteorder="big"))
        digest.update(relative_path)
        digest.update(len(content).to_bytes(8, byteorder="big"))
        digest.update(content)
    return digest.hexdigest()


def sha256_path_tree(path: Path) -> str:
    """Hash a file or directory tree with POSIX relative names."""

    path = path.resolve()
    if path.is_file():
        return sha256_tree_entries([(path.name, path.read_bytes())])
    entries = [
        (candidate.relative_to(path).as_posix(), candidate.read_bytes())
        for candidate in path.rglob("*")
        if candidate.is_file()
        and should_hash_relative_path(candidate.relative_to(path).as_posix())
    ]
    return sha256_tree_entries(entries)


def sha256_directory(path: Path) -> str:
    """Hash a directory tree by portable relative names and canonical content."""

    if not path.is_dir():
        raise ValueError(f"目录不存在：{path}")
    return sha256_path_tree(path)


def first_match_index(text: str, patterns: list[str]) -> tuple[int, str | None]:
    matches: list[tuple[int, str]] = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            matches.append((match.start(), pattern))
    return min(matches, default=(-1, None), key=lambda item: item[0])


def proxy_should_trigger(prompt: str, description: str) -> bool:
    engineering_signals = [
        r"修复|实现|bug|故障|报错|失败|无限轮询|重复扣费",
        r"代码|仓库|文件|函数|API|数据库|前端|后端|支付|状态机",
        r"测试|Vitest|typecheck|build|审查|重构|部署|生产级",
    ]
    prompt_is_engineering = any(regex_found(prompt, pattern) for pattern in engineering_signals)
    description_is_engineering = any(
        regex_found(description, pattern) for pattern in engineering_signals
    )
    delivery_signals = regex_found(
        prompt,
        r"修复|实现|落地|生产级|跨模块|完整验证|审查|重构|故障|失败|报错|无限轮询|重复扣费",
    )
    isolated_request = regex_found(
        prompt,
        r"解释.*代码|代码.*是什么意思|最简单.*代码片段|孤立代码片段",
    )
    if isolated_request and not delivery_signals:
        return False
    return prompt_is_engineering and description_is_engineering


def analyze_fixture(fixture_dir: Path) -> dict[str, Any]:
    fixture_dir = fixture_dir.resolve()
    config = json.loads((fixture_dir / "fixture.json").read_text(encoding="utf-8"))
    files = {
        str(path.relative_to(fixture_dir)).replace("\\", "/"): path.read_text(
            encoding="utf-8"
        )
        for path in fixture_dir.rglob("*")
        if path.is_file()
        and path.name != "fixture.json"
        and path.suffix != ".pyc"
        and "__pycache__" not in path.parts
    }
    combined = "\n".join(files.values())
    chain = {
        "submit": regex_found(combined, r"submit_video_job|submitVideoJob"),
        "enqueue": regex_found(combined, r"enqueue_video_job|enqueueVideoJob"),
        "process": regex_found(combined, r"process_video_job|processVideoJob"),
        "poll": regex_found(combined, r"pollVideoJob|shouldPollVideoJob"),
        "terminal": regex_found(combined, r"TERMINAL_.*STATES"),
        "display": "frontend/VideoResult.tsx" in files,
    }

    frontend = files.get("frontend/useVideoJob.ts", "")
    backend = files.get("backend/video_jobs.py", "")
    frontend_set = re.search(r"TERMINAL_STATES\s*=.*?\[(.*?)\]", frontend, re.DOTALL)
    frontend_states = set(
        re.findall(r"['\"]([a-z_]+)['\"]", frontend_set.group(1) if frontend_set else "")
    )
    backend_set = re.search(r"TERMINAL_VIDEO_JOB_STATES\s*=\s*\{(.*?)\}", backend)
    backend_states = set(
        re.findall(r"['\"]([a-z_]+)['\"]", backend_set.group(1) if backend_set else "")
    )
    defect_detected = "failed" in backend_states and "failed" not in frontend_states

    return {
        "source": display_path(
            fixture_dir,
            external_label="fixture",
            external_root=fixture_dir,
        ),
        "fixture": config["name"],
        "chain": chain,
        "chain_complete": all(chain.values()),
        "frontend_terminal_states": sorted(frontend_states),
        "backend_terminal_states": sorted(backend_states),
        "defect_detected": defect_detected,
        "detected_defect": config["expected_defect"] if defect_detected else None,
    }


def evaluate_check(
    artifact: Artifact, check: dict[str, Any], fixture: dict[str, Any], rubric: dict[str, Any]
) -> CheckResult:
    kind = check["kind"]
    evidence: list[str] = []
    passed = False

    if kind == "frontmatter":
        missing = [field for field in check["required_fields"] if not artifact.frontmatter.get(field)]
        name_ok = artifact.frontmatter.get("name") == check["expected_name"]
        description = artifact.frontmatter.get("description", "")
        length_ok = 0 < len(description) <= check["description_max_chars"]
        required_hits = {
            pattern: regex_found(description, pattern)
            for pattern in check.get("description_required_patterns", [])
        }
        forbidden_hits = [
            pattern
            for pattern in check.get("description_forbidden_patterns", [])
            if regex_found(description, pattern)
        ]
        passed = (
            not missing
            and name_ok
            and length_ok
            and all(required_hits.values())
            and not forbidden_hits
        )
        evidence = [
            f"缺失字段：{missing or '无'}",
            f"name 匹配：{name_ok}",
            f"description 字符数：{len(description)}/{check['description_max_chars']}",
            f"description 必需边界：{required_hits or '未配置'}",
            f"description 过宽模式：{forbidden_hits or '无'}",
        ]
    elif kind == "trigger_boundary":
        description = artifact.frontmatter.get("description", "")
        outcomes = []
        for item in rubric["trigger_tests"]:
            actual = proxy_should_trigger(item["prompt"], description)
            outcomes.append(actual == item["expected"])
            evidence.append(
                f"{item['id']}：expected={item['expected']} actual={actual}"
            )
        passed = all(outcomes)
    elif kind == "progressive_disclosure":
        links = re.findall(r"references/[A-Za-z0-9_.\-/]+\.md", artifact.core_text)
        conditional_hits = [
            pattern for pattern in check["conditional_terms"] if regex_found(artifact.core_text, pattern)
        ]
        forbidden_hits = [
            pattern
            for pattern in check["forbidden_unconditional_patterns"]
            if regex_found(artifact.core_text, pattern)
        ]
        passed = (
            len(set(links)) >= check["minimum_reference_links"]
            and bool(conditional_hits)
            and not forbidden_hits
        )
        evidence = [
            f"引用链接数：{len(set(links))}/{check['minimum_reference_links']}",
            f"按需条件命中：{conditional_hits or '无'}",
            f"无条件长加载违规：{forbidden_hits or '无'}",
        ]
    elif kind == "ordered_concepts":
        first_index, first_pattern = first_match_index(artifact.core_text, check["first"])
        then_index, then_pattern = first_match_index(artifact.core_text, check["then"])
        passed = first_index >= 0 and then_index >= 0 and first_index < then_index
        evidence = [
            f"前置概念：{first_pattern or '未找到'}@{first_index}",
            f"后置概念：{then_pattern or '未找到'}@{then_index}",
        ]
    elif kind == "capability":
        hits = {
            pattern: regex_found(artifact.capability_text, pattern)
            for pattern in check["patterns"]
        }
        passed = all(hits.values())
        evidence = [
            "能力可达文本：SKILL.md + "
            f"{len(artifact.routed_reference_paths)} 个模块化 routed references + "
            f"{len(artifact.forced_legacy_reference_paths)} 个 baseline 强制 legacy references",
            "Legacy exclusion："
            f"{artifact.legacy_excluded_reference_paths or '无'}",
            *[f"{pattern}：{'命中' if hit else '缺失'}" for pattern, hit in hits.items()],
        ]
    elif kind == "fixture":
        passed = fixture["chain_complete"] and fixture["defect_detected"]
        evidence = [
            f"链路完整：{fixture['chain_complete']} {fixture['chain']}",
            f"后端终态：{fixture['backend_terminal_states']}",
            f"前端终态：{fixture['frontend_terminal_states']}",
            f"缺陷识别：{fixture['defect_detected']}",
        ]
    elif kind == "context_efficiency":
        passed = artifact.default_context_chars <= check["max_default_context_chars"]
        evidence = [
            f"默认强制上下文字数代理：{artifact.default_context_chars}",
            f"上限：{check['max_default_context_chars']}",
            "该数值不等同于 tokenizer 精确 token 数。",
        ]
    else:
        evidence = [f"未知检查类型：{kind}"]

    return CheckResult(
        id=check["id"],
        title=check["title"],
        passed=passed,
        critical=bool(check["critical"]),
        weight=int(check["weight"]),
        evidence=evidence,
    )


def evaluate_artifact(
    artifact: Artifact, rubric: dict[str, Any], fixture: dict[str, Any]
) -> dict[str, Any]:
    results = [evaluate_check(artifact, check, fixture, rubric) for check in rubric["checks"]]
    total_weight = sum(result.weight for result in results)
    passed_weight = sum(result.weight for result in results if result.passed)
    score = round(100 * passed_weight / total_weight, 1) if total_weight else 0.0
    return {
        "artifact": {
            "label": artifact.label,
            "source": artifact.source,
            "core_path": artifact.core_path,
            "reference_count": len(artifact.reference_paths),
            "routed_reference_count": len(artifact.routed_reference_paths),
            "routed_reference_paths": artifact.routed_reference_paths,
            "forced_legacy_reference_count": len(artifact.forced_legacy_reference_paths),
            "forced_legacy_reference_paths": artifact.forced_legacy_reference_paths,
            "legacy_excluded_reference_count": len(
                artifact.legacy_excluded_reference_paths
            ),
            "legacy_excluded_reference_paths": artifact.legacy_excluded_reference_paths,
            "default_context_chars": artifact.default_context_chars,
            "content_sha256": sha256_text(artifact.all_text),
            "capability_text_sha256": sha256_text(artifact.capability_text),
            "tree_sha256": artifact.tree_sha256,
        },
        "score": score,
        "checks": [asdict(result) for result in results],
        "critical_failures": [
            result.id for result in results if result.critical and not result.passed
        ],
    }


def build_static_case_mapping(
    cases: list[dict[str, Any]], rubric: dict[str, Any], candidate: dict[str, Any]
) -> list[dict[str, Any]]:
    checks = {check["id"]: check for check in candidate["checks"]}
    reports = []
    for case in cases:
        expected = rubric["case_expectations"].get(case["id"], [])
        missing = [check_id for check_id in expected if not checks.get(check_id, {}).get("passed")]
        reports.append(
            {
                "id": case["id"],
                "prompt": case.get("prompt", ""),
                "static_status": "COVERED" if not missing else "UNCOVERED",
                "required_checks": expected,
                "missing_checks": missing,
                "note": "仅表示静态规则存在；未执行该 prompt，也不是 Agent 行为结果。",
            }
        )
    return reports


def render_markdown(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    candidate = report["candidate"]
    lines = [
        "# Production Delivery Orchestrator 离线评测",
        "",
        f"- 生成时间：`{report['metadata']['generated_at']}`",
        "- 模式：`offline_static_and_behavior_proxy`",
        "- LLM 调用：`0`",
        f"- Baseline Git ref：`{report['metadata']['baseline_git_ref'] or 'custom-path'}`",
        f"- 评测指纹：`{report['metadata']['evaluation_fingerprint']}`",
        f"- 最终状态：**{report['status']}**",
        "",
        "> 本报告没有运行真实 LLM，不能证明智能体已经在真实任务中遵守技能。它只验证静态提示词架构、规则覆盖、触发边界代理和最小代码库 fixture。",
        "",
        "## 对比结果",
        "",
        f"- Baseline source：`{baseline['artifact']['source']}`",
        f"- Candidate source：`{candidate['artifact']['source']}`",
        "",
        "| Artifact | Score | Critical failures |",
        "|---|---:|---|",
        f"| Baseline | {baseline['score']} | {', '.join(baseline['critical_failures']) or '无'} |",
        f"| Candidate | {candidate['score']} | {', '.join(candidate['critical_failures']) or '无'} |",
        f"| Delta | {report['comparison']['score_delta']:+.1f} | 最低要求 {report['comparison']['required_delta']:+.1f} |",
        "",
        "## 默认上下文代理",
        "",
        f"- Baseline：`{baseline['artifact']['default_context_chars']}` 字符",
        f"- Candidate：`{candidate['artifact']['default_context_chars']}` 字符",
        f"- 降幅：`{report['comparison']['context_reduction_percent']:.1f}%`（最低要求 `{report['comparison']['required_context_reduction_percent']:.1f}%`）",
        "- 这是强制初始加载字符量代理，不是 tokenizer 的精确 token 计数。",
        "",
        "## Capability 路由可达性",
        "",
        f"- Baseline 模块化 routed references：`{baseline['artifact']['routed_reference_count']}`",
        f"- Baseline 强制 legacy references：`{baseline['artifact']['forced_legacy_reference_count']}`；排除：`{baseline['artifact']['legacy_excluded_reference_paths'] or '无'}`",
        f"- Candidate 模块化 routed references：`{candidate['artifact']['routed_reference_count']}`",
        f"- Candidate 强制 legacy references：`{candidate['artifact']['forced_legacy_reference_count']}`；排除：`{candidate['artifact']['legacy_excluded_reference_paths'] or '无'}`",
        "- Capability 检查只搜索核心入口、入口路由到的模块化 references，以及 baseline 核心无条件强制加载的 legacy 长协议。完整内容哈希仍覆盖全部 references。",
        "",
        "## Candidate 检查",
        "",
    ]
    for check in candidate["checks"]:
        icon = "PASS" if check["passed"] else "FAIL"
        critical = "critical" if check["critical"] else "non-critical"
        lines.append(f"### {icon} `{check['id']}` — {check['title']} ({critical}, {check['weight']} 分)")
        lines.append("")
        for evidence in check["evidence"]:
            lines.append(f"- {evidence}")
        lines.append("")

    lines.extend([
        "## 静态场景规则映射（未执行 prompt）",
        "",
        "> COVERED 仅表示候选文本包含该场景所需规则，不表示真实 Agent 已执行或通过场景。",
        "",
        "| Case | Static status | Missing checks |",
        "|---|---|---|",
    ])
    for case in report["static_case_mapping"]:
        lines.append(
            f"| `{case['id']}` | {case['static_status']} | {', '.join(case['missing_checks']) or '无'} |"
        )

    fixture = report["fixture"]
    lines.extend(
        [
            "",
            "## Fixture 侦察",
            "",
            f"- Fixture source：`{fixture['source']}`",
            f"- 链路完整：`{fixture['chain_complete']}`",
            f"- 后端终态：`{fixture['backend_terminal_states']}`",
            f"- 前端终态：`{fixture['frontend_terminal_states']}`",
            f"- 识别预期缺陷：`{fixture['defect_detected']}`",
            "",
            "## 退出判定",
            "",
            f"- Candidate 最低分：`{report['comparison']['candidate_min_score']}`",
            f"- Candidate 实际分：`{candidate['score']}`",
            f"- 关键失败：`{report['critical_failures'] or '无'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def run_evaluation(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.baseline is None:
        preflight_default_git_baseline(
            args.baseline_git_ref, args.skill_relative_path
        )
    rubric = load_json_yaml(args.rubric)
    cases = parse_cases(args.cases)
    fixture = analyze_fixture(args.fixture)
    baseline_artifact = (
        load_artifact(
            args.baseline, "baseline", allow_forced_legacy_protocol=True
        )
        if args.baseline
        else load_git_artifact(
            args.baseline_git_ref,
            args.skill_relative_path,
            "baseline",
            allow_forced_legacy_protocol=True,
        )
    )
    candidate_artifact = load_artifact(args.candidate, "candidate")
    baseline = evaluate_artifact(baseline_artifact, rubric, fixture)
    candidate = evaluate_artifact(candidate_artifact, rubric, fixture)

    thresholds = rubric["thresholds"]
    delta = round(candidate["score"] - baseline["score"], 1)
    baseline_context = baseline["artifact"]["default_context_chars"]
    candidate_context = candidate["artifact"]["default_context_chars"]
    context_reduction = round(
        100 * (1 - candidate_context / baseline_context), 1
    ) if baseline_context else 0.0
    critical_failures = list(candidate["critical_failures"])
    if candidate["score"] < thresholds["candidate_min_score"]:
        critical_failures.append("candidate-min-score")
    if delta < thresholds["minimum_improvement_over_baseline"]:
        critical_failures.append("minimum-baseline-improvement")
    if context_reduction < thresholds["minimum_default_context_reduction_percent"]:
        critical_failures.append("minimum-default-context-reduction")

    baseline_ref = args.baseline_git_ref if not args.baseline else None
    input_hashes = {
        "runner_sha256": sha256_file(Path(__file__)),
        "rubric_sha256": sha256_file(args.rubric),
        "cases_sha256": sha256_file(args.cases),
        "fixture_content_sha256": sha256_directory(args.fixture.resolve()),
        "candidate_tree_sha256": candidate["artifact"]["tree_sha256"],
        "baseline_tree_sha256": baseline["artifact"]["tree_sha256"],
        "candidate_content_sha256": candidate["artifact"]["content_sha256"],
        "baseline_content_sha256": baseline["artifact"]["content_sha256"],
        "candidate_capability_text_sha256": candidate["artifact"][
            "capability_text_sha256"
        ],
        "baseline_capability_text_sha256": baseline["artifact"][
            "capability_text_sha256"
        ],
    }
    evaluation_fingerprint = sha256_text(
        json.dumps(input_hashes, sort_keys=True, ensure_ascii=False)
    )
    report = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evaluation_mode": rubric["evaluation_mode"],
            "llm_calls": 0,
            "disclaimer": rubric["disclaimer"],
            "cases_file": display_path(
                args.cases.resolve(),
                external_label="cases",
                external_root=args.cases.resolve(),
            ),
            "rubric_file": display_path(
                args.rubric.resolve(),
                external_label="rubric",
                external_root=args.rubric.resolve(),
            ),
            "baseline_git_ref": baseline_ref,
            "input_hashes": input_hashes,
            "evaluation_fingerprint": evaluation_fingerprint,
            "capability_routing": {
                "baseline": {
                    "routed_reference_count": baseline["artifact"][
                        "routed_reference_count"
                    ],
                    "forced_legacy_reference_count": baseline["artifact"][
                        "forced_legacy_reference_count"
                    ],
                    "legacy_excluded_reference_count": baseline["artifact"][
                        "legacy_excluded_reference_count"
                    ],
                },
                "candidate": {
                    "routed_reference_count": candidate["artifact"][
                        "routed_reference_count"
                    ],
                    "forced_legacy_reference_count": candidate["artifact"][
                        "forced_legacy_reference_count"
                    ],
                    "legacy_excluded_reference_count": candidate["artifact"][
                        "legacy_excluded_reference_count"
                    ],
                },
            },
        },
        "status": "PASS" if not critical_failures else "FAIL",
        "baseline": baseline,
        "candidate": candidate,
        "comparison": {
            "score_delta": delta,
            "required_delta": thresholds["minimum_improvement_over_baseline"],
            "candidate_min_score": thresholds["candidate_min_score"],
            "context_reduction_percent": context_reduction,
            "required_context_reduction_percent": thresholds[
                "minimum_default_context_reduction_percent"
            ],
        },
        "fixture": fixture,
        "static_case_mapping": build_static_case_mapping(cases, rubric, candidate),
        "critical_failures": critical_failures,
    }
    return report, 0 if report["status"] == "PASS" else 1


def run_self_test(args: argparse.Namespace) -> int:
    rubric = load_json_yaml(args.rubric)
    fixture = analyze_fixture(args.fixture)
    with tempfile.TemporaryDirectory(prefix="pdo-eval-selftest-") as temp_dir:
        bad_skill = Path(temp_dir) / "SKILL.md"
        bad_skill.write_text(
            "---\nname: wrong-name\ndescription: do everything\n---\n"
            "Always trust the agent. Everything passed.\n",
            encoding="utf-8",
        )
        artifact = load_artifact(bad_skill, "known-bad-self-test")
        result = evaluate_artifact(artifact, rubric, fixture)
        expected_failures = {
            "frontmatter-contract",
            "progressive-disclosure",
            "verification-honesty",
        }
        detected = expected_failures.issubset(set(result["critical_failures"]))

        legacy_only_skill = Path(temp_dir) / "legacy-only"
        legacy_references = legacy_only_skill / "references"
        legacy_references.mkdir(parents=True)
        (legacy_only_skill / "SKILL.md").write_text(
            "---\n"
            "name: production-delivery-orchestrator\n"
            "description: 用于模糊故障修复和生产级交付，不适用于普通问答。\n"
            "---\n"
            "# 路由入口\n\n"
            "`references/system-prompt.md` 仅供旧客户端兼容，不是模块化路由。\n",
            encoding="utf-8",
        )
        (legacy_references / "system-prompt.md").write_text(
            "独立审查；只读审查；Builder；修复后复验；P0/P1。\n",
            encoding="utf-8",
        )
        legacy_artifact = load_artifact(legacy_only_skill, "legacy-only-self-test")
        review_check = next(
            check for check in rubric["checks"] if check["id"] == "independent-review-loop"
        )
        legacy_result = evaluate_check(legacy_artifact, review_check, fixture, rubric)
        legacy_routing_detected = not legacy_result.passed

        modular_skill = Path(temp_dir) / "modular-route"
        modular_references = modular_skill / "references"
        modular_references.mkdir(parents=True)
        (modular_skill / "SKILL.md").write_text(
            "---\n"
            "name: production-delivery-orchestrator\n"
            "description: 用于模糊故障修复和生产级交付，不适用于普通问答。\n"
            "---\n"
            "需要独立审查时读取 `references/review-contract.md`。\n",
            encoding="utf-8",
        )
        (modular_references / "review-contract.md").write_text(
            "独立审查；只读审查；Builder；修复后复验；P0/P1。\n",
            encoding="utf-8",
        )
        modular_artifact = load_artifact(modular_skill, "modular-route-self-test")
        modular_result = evaluate_check(modular_artifact, review_check, fixture, rubric)
        modular_routing_detected = (
            modular_result.passed
            and len(modular_artifact.routed_reference_paths) == 1
            and not modular_artifact.forced_legacy_reference_paths
        )

        (legacy_only_skill / "SKILL.md").write_text(
            "---\n"
            "name: production-delivery-orchestrator\n"
            "description: 用于模糊故障修复和生产级交付，不适用于普通问答。\n"
            "---\n"
            "必须完整读取 `references/system-prompt.md`。\n",
            encoding="utf-8",
        )
        forced_baseline_artifact = load_artifact(
            legacy_only_skill,
            "forced-legacy-baseline-self-test",
            allow_forced_legacy_protocol=True,
        )
        forced_baseline_result = evaluate_check(
            forced_baseline_artifact, review_check, fixture, rubric
        )
        forced_baseline_detected = (
            forced_baseline_result.passed
            and len(forced_baseline_artifact.forced_legacy_reference_paths) == 1
            and not forced_baseline_artifact.legacy_excluded_reference_paths
        )

        detected = (
            detected
            and legacy_routing_detected
            and modular_routing_detected
            and forced_baseline_detected
        )
        print(
            json.dumps(
                {
                    "self_test": "PASS" if detected else "FAIL",
                    "expected_failures": sorted(expected_failures),
                    "detected_failures": result["critical_failures"],
                    "legacy_only_capability_rejected": legacy_routing_detected,
                    "modular_reference_capability_reached": modular_routing_detected,
                    "forced_baseline_legacy_reached": forced_baseline_detected,
                    "llm_calls": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if detected else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="无需付费 API 的 production-delivery-orchestrator 离线评测"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="可选的基线文件或目录；默认直接读取已发布 Git 基线。",
    )
    parser.add_argument("--baseline-git-ref", default=DEFAULT_BASELINE_GIT_REF)
    parser.add_argument("--skill-relative-path", default=DEFAULT_SKILL_RELATIVE_PATH)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--rubric", type=Path, default=EVAL_DIR / "rubric.yaml")
    parser.add_argument("--cases", type=Path, default=EVAL_DIR / "cases.yaml")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output-dir", type=Path, default=EVAL_DIR / "reports")
    parser.add_argument("--report-prefix", default="latest")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        args.report_prefix = validate_report_prefix(args.report_prefix)
    except ValueError as error:
        print(f"评测基础设施错误：{error}", file=sys.stderr)
        return 2
    if args.self_test:
        return run_self_test(args)

    try:
        report, exit_code = run_evaluation(args)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeError, ValueError) as error:
        print(f"评测基础设施错误：{error}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.report_prefix}.json"
    markdown_path = args.output_dir / f"{args.report_prefix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": report["status"],
                "baseline_score": report["baseline"]["score"],
                "candidate_score": report["candidate"]["score"],
                "score_delta": report["comparison"]["score_delta"],
                "context_reduction_percent": report["comparison"][
                    "context_reduction_percent"
                ],
                "critical_failures": report["critical_failures"],
                "json_report": display_path(
                    json_path.resolve(),
                    external_label="report",
                    external_root=args.output_dir.resolve(),
                ),
                "markdown_report": display_path(
                    markdown_path.resolve(),
                    external_label="report",
                    external_root=args.output_dir.resolve(),
                ),
                "llm_calls": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
