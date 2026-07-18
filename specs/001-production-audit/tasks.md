# Tasks: Production Audit and Reusable Delivery Workflow

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts](contracts/) and [quickstart.md](quickstart.md)

**Tests**: Required. Every behavior or current-fact repair gets a regression test before its
implementation. External tools get installation/probe evidence only; they do not replace project
tests.

## Phase 1: Specification Foundation

**Purpose**: Make the audit restart-safe and prevent undocumented scope expansion.

- [x] T001 Create and switch to the `001-production-audit` Git branch, then initialize the Spec Kit constitution and feature artifacts under `.specify/` and `specs/001-production-audit/`.
- [x] T002 Create `task_plan.md`, `findings.md`, `progress.md` and the A1–A9 workflow state in `workflow_status.md`.
- [x] T003 Validate specification coverage and task dependencies against `specs/001-production-audit/requirements-traceability.md`.

## Phase 2: Contract Regression Tests (Blocking Prerequisites)

**Purpose**: Encode existing guarantees before product files change.

- [x] T004 [P] Add current/historical document boundary regression cases in `.github/workflows/tests/test_current_state.py`.
- [x] T005 [P] Add UTF-8 stream and readable-help regression cases in `skills/production-delivery-orchestrator/tests/test_install_skill.py`.
- [x] T006 [P] Add missing-default-baseline and explicit-baseline recovery cases in `evals/production-delivery-orchestrator/tests/test_run_evals.py`.
- [x] T007 Run the new tests red and record their failure evidence in `progress.md` before implementation.

**Checkpoint**: The three confirmed findings are represented by failing, narrow tests.

## Phase 3: User Story 1 — Trust Current Delivery Facts (Priority: P1)

**Goal**: Readers see true installation, release and historical boundaries.

**Independent Test**: The documentation consistency suite rejects the prior transaction
contradiction and historical/current boundary regressions.

- [x] T008 [US1] Correct the multi-target installation transaction statement in `docs/codebase/CONCERNS.md` with source/test evidence.
- [x] T009 [US1] Add an explicit historical scope marker to `reviews/final-critic.md` without rewriting its original verdict.
- [x] T010 [US1] Extend current-state assertions in `.github/workflows/tests/test_current_state.py` to protect the corrected claims.
- [x] T011 [US1] Run `.github/workflows/tests/test_current_state.py` and document the fresh result in `progress.md`.

## Phase 4: User Story 2 — Run Consumer Commands Predictably (Priority: P1)

**Goal**: Consumer-facing installer/evaluator diagnostics are readable and actionable.

**Independent Test**: Installer console tests pass with a non-UTF-8-compatible stream and an
isolated no-history evaluator returns documented recovery guidance.

- [x] T012 [US2] Extract guarded UTF-8 console configuration in `skills/production-delivery-orchestrator/scripts/install_skill.py` without changing install transaction behavior.
- [x] T013 [US2] Add baseline-history preflight in `evals/production-delivery-orchestrator/run_evals.py` that preserves explicit `--baseline` behavior.
- [x] T014 [US2] Update consumer prerequisites, supported-version expectations and recovery guidance in `README.md`, `docs/codebase/STACK.md` and the applicable machine-readable metadata.
- [x] T015 [US2] Run installer and evaluator regression suites and record Windows/Linux boundary results in `progress.md`.

## Phase 5: User Story 3 — Resume a Complex Change Safely (Priority: P2)

**Goal**: Future contributors can use a compact, current, evidence-driven maintenance workflow.

**Independent Test**: A fresh reader can map an unfinished requirement to its task, evidence,
invalidating change and review gate without opening a historical report.

- [x] T016 [US3] Add a maintenance/audit contract under `skills/production-delivery-orchestrator/references/` that requires stale-fact checks before implementation and routes only applicable gates.
- [x] T017 [US3] Update `skills/production-delivery-orchestrator/SKILL.md`, `skills/registry.json` and related evaluator expectations for the new reference without forcing it on low-risk tasks.
- [x] T018 [US3] Create a current audit matrix and test ledger under `docs/audits/` from `requirements-traceability.md` and `progress.md`.
- [x] T019 [US3] Run registry generation, evaluator and reference/contract regression tests; record evidence in `progress.md`.

## Phase 6: User Story 4 — Learn the Change Without Replaying It (Priority: P2)

**Goal**: A reviewer can read a local HTML handoff and demonstrate understanding through a quiz.

**Independent Test**: A structural test confirms required sections/links and a headless local
browser or DOM harness verifies correct and incorrect quiz feedback.

- [x] T020 [P] [US4] Create `docs/reports/production-audit-closure-2026-07-18.html` with context, decisions, changed behavior, evidence, limits and a scored quiz.
- [x] T021 [US4] Add report structure/quiz regression validation under `tools/tests/` or `.github/workflows/tests/` and a local `webapp-testing`/Playwright browser journey when the installed browser runtime is usable.
- [x] T022 [US4] Run both the static report test and the local browser journey; if browser execution is unavailable, record the exact setup failure and do not call interaction behavior verified.

## Phase 7: External Capability Validation

**Purpose**: Verify the tools requested by the user without introducing unrelated authority.

- [x] T023 [P] Read and minimally invoke or classify each requested local skill (create-plan, frontend/design, CI, Playwright, MCP, Figma, planning, threat-model, CLI and PR-review) in `docs/audits/`, marking method-only or not-applicable skills honestly.
- [x] T024 [P] Inspect pinned Addy Osmani skill inventory with `npx skills --list` and install only non-colliding review/TDD capabilities if the CLI supports a scoped target.
- [x] T025 [P] Install Understand Anything only after link-collision preflight; verify files and commands without representing an unavailable graph/model run as success.
- [x] T026 Record Composio, awesome-llm-apps and Superpowers as classified external references rather than unneeded runtime dependencies in `docs/audits/`.

## Phase 8: Cross-Cutting Validation and Independent Review

**Purpose**: Prevent local green tests or generated docs from being mistaken for final closure.

- [x] T027 Run the full applicable local quality sequence from `specs/001-production-audit/quickstart.md`, including generated-file and release verification checks.
- [x] T028 Run `git diff --check`, verify no generated secret/agent credential files are staged, and update `workflow_status.md`, `task_plan.md`, `findings.md` and `progress.md`.
- [x] T029 Request an independent read-only six-dimension review and save its findings under `reviews/`.
- [x] T030 Fix every in-scope reviewer finding, rerun affected tests and request the same reviewer to re-verify.
- [ ] T031 Commit and push only after reviewer approval; wait for dual-platform CI and record its immutable run evidence.

## Dependencies and Execution Order

- T001–T003 establish the specification and must precede code remediation.
- T004–T007 are the red-test gate for T008–T015.
- US1 and US2 can execute in parallel only after T007 because they own non-overlapping files.
- US3 depends on verified US1/US2 facts because its reusable contract must not encode stale behavior.
- US4 and external validation may run in parallel after the current facts are fixed.
- T027–T031 depend on all selected implementation and external-validation tasks.

## MVP Scope

Complete T004–T015 first. This closes the currently demonstrated P1 documentation fact drift and
P2 Windows/shallow-history consumer failures before any optional capability or report work.
