# Implementation Plan: Production Audit and Reusable Delivery Workflow

**Branch**: `001-production-audit` | **Date**: 2026-07-18 | **Spec**: [spec.md](spec.md)

## Summary

Repair verified consumer and maintainer risks without changing the published v1.7.0 tag:
make documentation facts fail-closed, make Windows command diagnostics readable, make missing
evaluation history actionable, and preserve a reusable requirements-to-evidence workflow. Use
existing standard-library patterns and tests; external tools are scoped capability evidence, not
new runtime dependencies.

## Technical Context

**Language/Version**: Python 3.11.

**Primary Dependencies**: Python standard library; optional Node `npx skills` for consumer
discovery; optional agent CLIs only for isolated evidence collection.

**Storage**: Versioned Markdown/JSON, Git history and release assets; no database.

**Testing**: Python `unittest`, stdlib `trace`, GitHub Actions dual-platform matrix, isolated
temporary directories and optional real-agent fixture matrix.

**Target Platform**: Windows and Linux; macOS consumer documentation remains compatible but is
not an asserted CI platform.

**Project Type**: Agent Skills distribution, installer, offline evaluator and release builder.

**Performance Goals**: Local preflight must fail before expensive evaluation work when required
Git history is absent; installer help must return immediately and remain readable. No high-QPS
service exists in scope.

**Constraints**: Preserve existing CLI behavior and published tag; no new mandatory dependency,
network call, credential persistence or global configuration overwrite; tests must be hermetic.

**Scale/Scope**: One distributable skill, nine modular references, three supported CLI profiles,
dual-platform CI and a single current-state entry point.

## Constitution Check

*Pre-design: PASS. Post-design: PASS.*

| Principle | Design response |
|---|---|
| Evidence Before Claims | Add narrow tests for documentation facts and missing-history error text; preserve partial real-CLI status. |
| Transactional, Bounded Installation | Do not alter installation targets or rollback behavior; correct its documentation and test console output only. |
| Cross-Platform Contract Fidelity | Reuse the existing guarded UTF-8 stream configuration pattern and test it with a non-UTF-8 console surrogate. |
| Minimal Authority and Supply-Chain Integrity | Pin/record external sources; do not configure Composio, paid models or global plugins without a scoped validation need. |
| Progressive, Maintainable Delivery | Use Spec Kit tasks, focused regression tests, independent review and versioned handoff artifacts. |

## Project Structure

### Documentation (this feature)

```text
specs/001-production-audit/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── requirements-traceability.md
├── contracts/
│   ├── consumer-command-contract.md
│   └── evidence-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source and verification surface

```text
skills/production-delivery-orchestrator/
├── scripts/install_skill.py
└── tests/test_install_skill.py
evals/production-delivery-orchestrator/
├── run_evals.py
└── tests/test_run_evals.py
.github/workflows/tests/test_current_state.py
docs/codebase/CONCERNS.md
docs/current-state.md
reviews/final-critic.md
workflow_status.md
docs/reports/production-audit-closure-2026-07-18.html
```

**Structure Decision**: Keep the existing package layout. The remediation belongs beside the
installer/evaluator contracts and their tests; evidence and handoff files belong in `docs/` and
the feature specification rather than a new application layer.

## Complexity Tracking

No constitution violation is required. Explicit baseline input reuses the existing CLI option;
the preflight is a diagnostic guard, not a new artifact service or fallback transport.
