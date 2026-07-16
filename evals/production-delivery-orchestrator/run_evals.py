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
from pathlib import Path
from typing import Any


EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
DEFAULT_CANDIDATE = REPO_ROOT / "skills" / "production-delivery-orchestrator"
DEFAULT_FIXTURE = EVAL_DIR / "fixtures" / "video-polling-state-machine"
DEFAULT_BASELINE_GIT_REF = "b3d9a17"
DEFAULT_SKILL_RELATIVE_PATH = "skills/production-delivery-orchestrator"


@dataclass
class Artifact:
    label: str
    source: str
    core_path: str
    core_text: str
    all_text: str
    frontmatter: dict[str, str]
    reference_paths: list[str]
    default_context_chars: int


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


def calculate_default_context_chars(core_text: str, reference_texts: list[str]) -> int:
    """Estimate the initial forced prompt surface, not eventual on-demand reads."""

    unconditional_patterns = (
        r"必须完整读取\s*`?references/system-prompt\.md`?",
        r"始终完整读取",
        r"不得用摘要替代",
    )
    forces_all = any(regex_found(core_text, pattern) for pattern in unconditional_patterns)
    return len(core_text) + (sum(map(len, reference_texts)) if forces_all else 0)


def load_artifact(path: Path, label: str) -> Artifact:
    path = path.resolve()
    if path.is_dir():
        core_path = path / "SKILL.md"
        root = path
    else:
        core_path = path
        root = path.parent

    if not core_path.is_file():
        raise FileNotFoundError(f"{label} 缺少 SKILL.md 或 Markdown 文件：{path}")

    core_text = core_path.read_text(encoding="utf-8")
    frontmatter, _ = split_frontmatter(core_text)
    reference_paths: list[str] = []
    reference_texts: list[str] = []
    references_dir = root / "references"
    if core_path.name == "SKILL.md" and references_dir.is_dir():
        for reference in sorted(references_dir.rglob("*.md")):
            reference_paths.append(str(reference))
            reference_texts.append(reference.read_text(encoding="utf-8"))

    return Artifact(
        label=label,
        source=str(path),
        core_path=str(core_path),
        core_text=core_text,
        all_text="\n".join([core_text, *reference_texts]),
        frontmatter=frontmatter,
        reference_paths=reference_paths,
        default_context_chars=calculate_default_context_chars(core_text, reference_texts),
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


def load_git_artifact(ref: str, skill_relative_path: str, label: str) -> Artifact:
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
    return Artifact(
        label=label,
        source=f"git:{ref}:{skill_relative_path}",
        core_path=f"git:{ref}:{core_path}",
        core_text=core_text,
        all_text="\n".join([core_text, *reference_texts]),
        frontmatter=frontmatter,
        reference_paths=reference_paths,
        default_context_chars=calculate_default_context_chars(core_text, reference_texts),
    )


def regex_found(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        hits = {pattern: regex_found(artifact.all_text, pattern) for pattern in check["patterns"]}
        passed = all(hits.values())
        evidence = [f"{pattern}：{'命中' if hit else '缺失'}" for pattern, hit in hits.items()]
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
            "default_context_chars": artifact.default_context_chars,
            "content_sha256": sha256_text(artifact.all_text),
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
    rubric = load_json_yaml(args.rubric)
    cases = parse_cases(args.cases)
    fixture = analyze_fixture(args.fixture)
    baseline_artifact = (
        load_artifact(args.baseline, "baseline")
        if args.baseline
        else load_git_artifact(
            args.baseline_git_ref, args.skill_relative_path, "baseline"
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
        "candidate_content_sha256": candidate["artifact"]["content_sha256"],
        "baseline_content_sha256": baseline["artifact"]["content_sha256"],
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
            "cases_file": str(args.cases.resolve()),
            "rubric_file": str(args.rubric.resolve()),
            "baseline_git_ref": baseline_ref,
            "input_hashes": input_hashes,
            "evaluation_fingerprint": evaluation_fingerprint,
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
        print(
            json.dumps(
                {
                    "self_test": "PASS" if detected else "FAIL",
                    "expected_failures": sorted(expected_failures),
                    "detected_failures": result["critical_failures"],
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
                "json_report": str(json_path.resolve()),
                "markdown_report": str(markdown_path.resolve()),
                "llm_calls": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
