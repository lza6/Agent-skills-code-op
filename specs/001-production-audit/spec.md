# Feature Specification: Production Audit and Reusable Delivery Workflow

**Feature Branch**: `001-production-audit`

**Created**: 2026-07-18

**Status**: Ready for planning

**Input**: Transform the current production skill repository into a truthfully audited,
reusable delivery workflow. Verify requested skills and external tools, fix actual
compatibility/documentation gaps, preserve release facts, provide an HTML handoff report and
close the loop with independent review.

## User Scenarios and Testing *(mandatory)*

### User Story 1 - Trust Current Delivery Facts (Priority: P1)

As a maintainer, I can identify which release, CLI behavior and installation guarantees are
current, historical, partial or externally blocked, so that I do not make production decisions
from stale reports.

**Why this priority**: Incorrect release or transaction information directly causes unsafe
installation and support decisions.

**Independent Test**: A repository consistency check rejects a deliberate contradiction between
current documentation and the installer/release facts, while historical reports remain clearly
labelled rather than silently treated as current.

**Acceptance Scenarios**:

1. **Given** a maintainer reads the current state and codebase concerns, **When** the installer
   guarantees a multi-target rollback, **Then** no current document says that the guarantee is
   absent.
2. **Given** an old review is linked for context, **When** a reader opens it, **Then** its
   historical scope and non-current status are explicit.
3. **Given** Claude or Gemini has no usable controlled access, **When** current documentation is
   checked, **Then** the real-client matrix remains partial rather than reported as passing.

---

### User Story 2 - Run Consumer Commands Predictably (Priority: P1)

As a Windows or Linux consumer, I receive readable diagnostics and safe next steps when I
inspect the installer or run evaluation in an unsupported checkout, so that I can recover
without guessing or corrupting an installation.

**Why this priority**: Installation and evaluation are the public product path for this
repository.

**Independent Test**: Automated tests cover Windows UTF-8 console behavior and an evaluator
without required baseline history, including a successful documented recovery route.

**Acceptance Scenarios**:

1. **Given** a Windows-compatible console, **When** a consumer requests installer help, **Then**
   Chinese help text is readable and the command returns normally.
2. **Given** a shallow clone or source archive without the default baseline, **When** a consumer
   runs evaluation without an explicit baseline, **Then** it exits nonzero with an actionable
   explanation rather than an opaque Git error.
3. **Given** a consumer supplies a valid explicit baseline, **When** the evaluator runs, **Then**
   it preserves candidate and known-bad comparison safeguards.

---

### User Story 3 - Resume a Complex Change Safely (Priority: P2)

As a solo developer, I can start a future feature from persistent requirements, task
dependencies, acceptance evidence and an up-to-date workflow, so that a later Agent session
does not repeat stale assumptions or skip review.

**Why this priority**: The repository distributes a delivery workflow; its own maintenance must
meet the workflow's standard.

**Independent Test**: A new reader can use the workflow, requirement matrix and test ledger to
locate the next unfinished task, its prerequisites and its validation command.

**Acceptance Scenarios**:

1. **Given** a task spans multiple sessions, **When** a maintainer opens the planning files,
   **Then** they can identify the current phase, completed evidence, open risk and next action.
2. **Given** a change completes local tests, **When** it is declared ready, **Then** the task
   records a separate independent reviewer gate and re-review requirement.

---

### User Story 4 - Learn the Change Without Replaying the Work (Priority: P2)

As a reviewer or future maintainer, I can open a standalone HTML report and pass its short
quiz, so that I understand the context, decisions, changed behavior, evidence and remaining
external limits.

**Why this priority**: The requested handoff must teach rather than merely list files.

**Independent Test**: The report renders locally without a build step, contains the required
sections, and the quiz gives immediate feedback for correct and incorrect answers.

**Acceptance Scenarios**:

1. **Given** the report is opened from disk, **When** the reader completes the quiz, **Then** it
   scores the answers and explains any incorrect choice.
2. **Given** the reader follows report links, **When** they inspect supporting evidence, **Then**
   each link resolves to a repository-relative artifact or an explicitly external URL.

### Edge Cases

- A generated graph, static evaluation, CLI probe or release artifact may be useful evidence but
  must not be promoted to real-model, security or deployment proof.
- An external tool installer may write global links; an existing real directory, link collision,
  missing Node runtime or absent model entitlement must stop safely and preserve user state.
- A document can be historically correct yet operationally dangerous if it is presented as a
  current guarantee.
- A test run in a shallow checkout must never silently compare against an arbitrary fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST contain a requirement trace that maps every applicable request
  to an implementation, test, document, explicit external block or not-applicable rationale.
- **FR-002**: Current documentation MUST accurately describe installation transaction behavior,
  release status and real-client evidence; historic documents MUST state their time boundary.
- **FR-003**: Consumers MUST receive readable, deterministic installer diagnostics on supported
  Windows and Linux command environments.
- **FR-004**: Evaluation MUST identify a missing default baseline/history prerequisite before it
  performs comparison work and MUST state the supported recovery command.
- **FR-005**: The project MUST preserve its existing candidate, known-bad, release verification
  and supply-chain safeguards while adding diagnostics.
- **FR-006**: The project MUST persist a dependency-aware plan, task state, findings and test
  evidence that a future session can resume.
- **FR-007**: The project MUST publish a self-contained HTML handoff with a scored comprehension
  quiz and links to supporting evidence.
- **FR-008**: The project MUST perform an independent, read-only six-dimension review after
  implementation and re-run it after any reviewer-driven repair.
- **FR-009**: External skills, plugins and tools MUST be classified as installed, safely verified,
  not applicable, unavailable or externally blocked; no missing credential or model result may
  be described as a successful invocation.
- **FR-010**: The immutable v1.7.0 tag and its release artifacts MUST remain unchanged by this
  work.

### Key Entities

- **Requirement Trace**: A durable mapping from an explicit or inferred requirement to its scope,
  status, evidence, risk and next action.
- **Audit Finding**: A prioritized, evidence-backed issue with owner, remediation task,
  acceptance condition and reviewer disposition.
- **Evidence Record**: A command, environment boundary, outcome and freshness condition that
  supports a narrow claim.
- **Capability Record**: A skill, plugin or CLI source, version/commit, applicability, minimum
  validation and permission boundary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every applicable requirement in this specification has at least one linked task
  and an evidence or explicit-block entry before delivery.
- **SC-002**: All automated checks added or changed by this feature pass on the supported local
  environment and the remote dual-platform quality workflow passes after merge.
- **SC-003**: A deliberate current-document contradiction and a missing-history evaluator fixture
  are both rejected by automated tests.
- **SC-004**: A consumer can identify the next action for each partial or blocked area from one
  current document without reading historical reports.
- **SC-005**: The HTML report renders locally and its quiz returns immediate scored feedback for
  every answer option.

## Assumptions

- Existing v1.7.0 release facts remain the stable baseline; this work creates a later source
  commit rather than modifying an existing tag or asset.
- Python 3.11, Git and the existing standard-library test tooling remain available on supported
  platforms.
- No short-lived Claude/Gemini credential or paid model budget is supplied; their matrix remains
  a documented external block unless a controlled account becomes available.
- External UI/Figma, web E2E, MCP server and Composio work are capability validations only; the
  current repository has no matching product surface to implement.
