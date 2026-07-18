<!--
Sync Impact Report
- Version: template → 1.0.0 (initial project constitution)
- Modified principles: replaced all template placeholders with five project principles.
- Added sections: Runtime and safety constraints; workflow and quality gates.
- Template impact: .specify/templates/{spec,plan,tasks}-template.md are generic and
  already contain user scenario, constitution-check and dependency sections; no edits
  required. Codex integration skills are agent-neutral and contain no stale Claude-only
  runtime guidance.
- Deferred items: none.
-->
# Agent Skills Code OP Constitution

## Core Principles

### I. Evidence Before Claims
Every current-state, compatibility, release, security and performance claim MUST link to
fresh, reproducible evidence. Historical reports MUST be labelled as historical. A mock,
static evaluator, CLI probe or build result MUST NOT be described as a successful real
Agent execution, deployment or user journey.

### II. Transactional, Bounded Installation
Installers and project bridges MUST preserve user files, reject resolved paths outside the
intended target and leave no untracked partial state on failure. Multi-target changes MUST
have preflight, rollback/recovery and regression coverage for path, link and interruption
boundaries.

### III. Cross-Platform Contract Fidelity
Public commands, exit codes, artifacts and reports MUST behave consistently on supported
Windows and Linux environments. Platform differences such as launchers, console encodings,
paths and process groups require explicit contracts and negative tests rather than implicit
host assumptions.

### IV. Minimal Authority and Supply-Chain Integrity
Sensitive host configuration, credentials, network proxy settings, external model calls and
publishing require explicit opt-in. CI actions MUST be full-commit pinned; release metadata,
checksums, provenance and attestations MUST remain mutually consistent. No secret, token or
absolute host path may enter tracked reports.

### V. Progressive, Maintainable Delivery
Use the smallest compatible change that closes the verified risk. Complex work MUST begin
with a specification, dependency-aware plan and acceptance evidence; tests precede changed
logic when a behavioral regression can be expressed. Documentation and machine-readable
inventories are part of the public contract, not optional afterthoughts.

## Runtime and Safety Constraints

The supported automation baseline is Python 3.11 standard library on Windows and Linux.
Node-based discovery is an optional consumer dependency, not a build dependency. Real Agent
CLI experiments run only in temporary fixtures with an explicit unsafe-execution flag and
minimal credentials outside the repository. This repository is a skill distribution,
installation, evaluation and release system; frontend, database, business API and SaaS data
requirements are not applicable unless a future feature adds those surfaces.

## Workflow and Quality Gates

For a multi-file or public-contract change, create or update a Spec Kit feature under
`specs/`, map requirements to tasks, and record evidence in `workflow_status.md` plus the
planning files. Before merging, run the affected unit/integration suites, generated-file
checks, release verification and whitespace check. An independent read-only reviewer must
assess requirement coverage, correctness, boundary cases, code quality, test evidence and
actual execution results; the implementer fixes findings and requests re-verification.

## Governance

This constitution governs new work and supersedes unlabelled historical instructions. A
change that alters these principles requires a versioned amendment, impact report and
updates to affected templates or runtime guidance. Semantic versioning applies: MAJOR for
removed/redefined principles, MINOR for new material principles and PATCH for clarification.
Every release or audit must distinguish verified, partial, not applicable and externally
blocked outcomes. The canonical current-state entry point is `docs/current-state.md`; this
constitution and `workflow_status.md` provide the process and evidence trail.

**Version**: 1.0.0 | **Ratified**: 2026-07-18 | **Last Amended**: 2026-07-18
