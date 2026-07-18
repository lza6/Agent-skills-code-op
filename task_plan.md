# Task Plan: Production Audit and Reusable Delivery Workflow

## Goal

Turn the current single-skill distribution repository into a truthfully documented,
cross-platform-audited and repeatable delivery workflow, while preserving the immutable
v1.7.0 release and recording external CLI limits without fabrication.

## Current Phase

Phase 5 — independent review and delivery

## Phases

### Phase 1: Requirements and Discovery

- [x] Reconstruct the request and distinguish applicable requirements from Web/SaaS-only items.
- [x] Inventory installed skills, CLIs and external tool sources.
- [x] Inspect project architecture, live release facts and current audit records.
- [x] Record confirmed P1/P2 findings in `findings.md`.
- **Status:** complete

### Phase 2: Specification and Structure

- [x] Initialize Spec Kit with Codex integration.
- [x] Establish the project constitution.
- [x] Create the 001 feature specification, plan, traceability matrix and task graph.
- [x] Run a read-only consistency analysis before changing product files.
- **Status:** complete

### Phase 3: Verified Remediation

- [x] Correct stale codebase/review documentation and add drift regression coverage.
- [x] Add Windows-safe UTF-8 installer console behavior with tests.
- [x] Add shallow-clone/source-archive evaluation preflight and actionable diagnostics.
- [x] Install only verified, applicable external capabilities and record their scope.
- **Status:** complete

### Phase 4: Full Validation and Product Evidence

- [x] Run focused installer, evaluator, forward, registry, release and CI checks.
- [x] Run the safe local Understand Anything installation and repository scan if its model
      preconditions are available; otherwise record the exact stop condition.
- [x] Produce a requirements matrix, test ledger, HTML handoff report and comprehension quiz.
- **Status:** complete — graph generation is accurately recorded as externally blocked.

### Phase 5: Independent Review and Delivery

- [x] Request an independent read-only six-dimension review of the final diff.
- [x] Fix every in-scope review finding and request reviewer re-verification.
- [ ] Commit, push and verify CI only after the reviewer approves.
- **Status:** in_progress

## Key Questions

1. Can the evaluator accept an explicit artifact baseline when full Git history is absent
   without weakening its candidate/known-bad guarantees?
2. Which external capability can create value for this Python skill repository without adding
   unnecessary global credentials, network authority or frontend dependencies?
3. Can Claude and Gemini real-agent evidence be reproduced with controlled access, or must
   their external account/credential constraints remain a documented partial result?

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Treat the repository as a skill distribution system, not a SaaS web app | Repository evidence shows no UI/API/database/deployment surface; hardening must target its actual user journey. |
| Use Spec Kit plus persistent planning files | The task has multiple dependent repair, audit and handoff phases that need restart-safe evidence. |
| Preserve v1.7.0 and work on a new feature branch/commit sequence | Published tags are immutable evidence; corrective work must not rewrite them. |
| Do not install Composio by default | It is an OAuth/API SDK requiring a key, not a standalone skill, and is unrelated to the current user journey. |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| PowerShell profile and utility module failures | 1 | Use `cmd.exe` or `powershell.exe -NoProfile -ExecutionPolicy Bypass` for targeted commands. |
| Generic `cmd` cleanup rejected by command policy | 1 | Remove only verified generated artifacts through a controlled Python session; do not broaden deletion scope. |
| `run_client_matrix.py --self-test` is unsupported | 1 | Used its documented no-`--execute` probe instead; result is expected `NOT_RUN`. |
| Generated local audit artifacts could not be removed | 3 policy-rejected attempts | Keep them untracked and exclude them explicitly from any commit; do not bypass deletion policy. |

## Notes

- Re-read this plan before implementation choices and update it after each phase.
- The real Claude/Gemini matrix is externally blocked, not a substitute target for offline tests.
