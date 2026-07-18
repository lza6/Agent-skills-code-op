#!/usr/bin/env python3
"""Audit a stdlib ``trace --count`` result against a checked-in line baseline.

This intentionally reports line-coverage only.  It is an audit gate for the
selected runner tests, not a substitute for branch coverage or real CLI E2E.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACE_COUNT_RE = re.compile(r"^\s*(\d+):")


def parse_trace_counts(path: Path) -> set[int]:
    """Return one-based source lines executed by ``trace --count``."""

    counts: set[int] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if TRACE_COUNT_RE.match(line):
            counts.add(line_number)
    return counts


def counted_source_lines(path: Path) -> set[int]:
    """Use non-empty, non-comment physical lines as a portable audit denominator."""

    return {
        line_number
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if (stripped := line.strip()) and not stripped.startswith("#")
    }


def trace_cover_path(trace_dir: Path, relative_source: str) -> Path:
    source = Path(relative_source)
    return trace_dir / (source.with_suffix("").as_posix().replace("/", ".") + ".cover")


def build_report(
    *,
    trace_dir: Path,
    sources: dict[str, Path],
    cover_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Build deterministic metrics for selected source files."""

    targets: list[dict[str, Any]] = []
    for relative_source in sorted(sources):
        source = sources[relative_source]
        cover = (cover_paths or {}).get(relative_source) or trace_cover_path(
            trace_dir, relative_source
        )
        if not source.is_file():
            raise ValueError(f"source 不存在: {relative_source}")
        if not cover.is_file():
            raise ValueError(f"缺少 trace 覆盖结果: {relative_source}")
        source_lines = counted_source_lines(source)
        executed_lines = parse_trace_counts(cover) & source_lines
        total = len(source_lines)
        if total == 0:
            raise ValueError(f"source 没有可审计代码行: {relative_source}")
        targets.append(
            {
                "path": relative_source,
                "source_lines": total,
                "executed_lines": len(executed_lines),
                "line_coverage": round(len(executed_lines) / total, 4),
            }
        )
    return {
        "schema": 1,
        "method": "stdlib-trace-line-audit",
        "targets": targets,
    }


def baseline_errors(report: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    if baseline.get("schema") != 1:
        return ["baseline schema 必须为 1"]
    actual = {
        target.get("path"): target.get("line_coverage")
        for target in report.get("targets", [])
        if isinstance(target, dict)
    }
    errors: list[str] = []
    for target in baseline.get("targets", []):
        if not isinstance(target, dict) or not isinstance(target.get("path"), str):
            errors.append("baseline target 无效")
            continue
        path = target["path"]
        minimum = target.get("minimum_line_coverage")
        observed = actual.get(path)
        if not isinstance(minimum, (int, float)):
            errors.append(f"baseline {path} 缺少 minimum_line_coverage")
        elif not isinstance(observed, (int, float)):
            errors.append(f"缺少目标 coverage: {path}")
        elif observed < minimum:
            errors.append(f"{path} coverage {observed:.4f} 低于基线 {minimum:.4f}")
    return errors


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def relative_source(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError as error:
        raise ValueError(f"source 必须位于仓库内: {path}") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 stdlib trace line coverage 基线")
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        sources = {relative_source(path): path.resolve() for path in args.source}
        report = build_report(trace_dir=args.trace_dir, sources=sources)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_json(report), encoding="utf-8")
        errors: list[str] = []
        if args.baseline is not None:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            errors = baseline_errors(report, baseline)
        result = {
            "status": "PASS" if not errors else "FAIL",
            "report": args.output.as_posix(),
            "errors": errors,
        }
        print(render_json(result).rstrip())
        return 0 if not args.check or not errors else 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(render_json({"status": "FAIL", "error": f"{type(error).__name__}: {error}"}).rstrip())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
