# Evidence Data Model

This feature adds no database or persisted runtime model. These documentation entities define
the records that must remain traceable across files.

## Requirement Trace

| Field | Meaning | Validation |
|---|---|---|
| identifier | Stable requirement ID such as FR-003 | Unique within the feature specification |
| scope | Applicable, not applicable or externally blocked | Must include rationale for non-applicable/blocked |
| implementation | Files and functions that meet the requirement | Must be repository-relative |
| verification | Test or command evidence | Must state expected outcome and freshness |
| risk | P0–P3 or external boundary | Must have a next action unless closed |

## Audit Finding

| Field | Meaning | Validation |
|---|---|---|
| identifier | Stable audit/task ID | Unique in `tasks.md` and workflow status |
| severity | P0, P1, P2, P3 or external-blocked | P0/P1 cannot be marked closed without evidence |
| root cause | Falsifiable explanation | Links to code or test evidence |
| remediation | Minimal corrective change | States compatibility impact |
| reviewer state | Open, fixed, verified or blocked | Only independent review can mark verified |

## Evidence Record

| Field | Meaning | Validation |
|---|---|---|
| claim | Narrow assertion supported by the record | Cannot exceed command/test scope |
| command | Reproducible command or inspection | Must not contain secrets |
| environment | Platform and prerequisite boundary | Windows/Linux/credential condition explicit |
| result | Pass, fail, partial, blocked or not applicable | Failure cannot be relabelled as pass |
| freshness trigger | Change that invalidates evidence | Linked to affected files/contracts |
