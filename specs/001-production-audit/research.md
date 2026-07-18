# Research: Production Audit and Reusable Delivery Workflow

## Decision: Preserve the existing standard-library runtime

**Rationale**: The project is deliberately stdlib-only and already has dual-platform CI. Adding
a console, graph or planning package to the product would expand the consumer attack surface for
no installer/evaluator benefit.

**Alternatives considered**:

- Add a third-party logging/encoding library: rejected because guarded native stream
  reconfiguration is sufficient and dependency-free.
- Ignore Windows console encoding: rejected because a consumer-facing Chinese help screen is
  unreadable on the verified command path.

## Decision: Fail early on unavailable Git baseline

**Rationale**: `run_evals.py` currently invokes Git directly for default baseline `b3d9a17`.
An explicit preflight can tell a shallow-clone/source-archive consumer to supply `--baseline`
or fetch the required history before rubric/candidate work begins.

**Alternatives considered**:

- Silently use the current candidate as baseline: rejected because it invalidates comparison and
  known-bad guarantees.
- Bundle a baseline copy implicitly: rejected because a hidden copy can drift from the declared
  Git baseline and complicates provenance.
- Add an explicit release-artifact baseline later: viable future P3, but out of this focused
  change until its provenance and version-selection contract are designed.

## Decision: Treat capability sources by category

| Capability | Decision | Rationale |
|---|---|---|
| Existing local skills | Validate and use by scope | All requested skills except Composio are already mirrored in local Codex/Agents/Claude roots. |
| Spec Kit | Initialize and use | `specify 0.12.16` is installed and produces durable specifications without a product runtime dependency. |
| Understand Anything | Install/verify only in a controlled scope | It creates global links and graph generation may consume model tokens; graph is navigation evidence, not correctness proof. |
| Addy Osmani agent skills | Inspect pinned skill listing; install only code-review/TDD skill if no collision | Its collection is relevant to audit discipline, but it must not replace project-specific contracts. |
| obra/superpowers | Reuse local compatible workflow concepts | Official plugin installation is client-specific; unverified marketplace installation is not needed to validate the current repository. |
| Composio | Do not install | It is an OAuth/API-key SDK unrelated to this repository's path and would introduce external authority. |
| awesome-llm-apps | Research-only reference | It is an application/template collection, not a dependency or generic skill installer. |

## Decision: Correct historical context without erasing it

**Rationale**: Historical critic records retain audit value, but they must never look like a
v1.7 current-state guarantee. Add visible historical markers and test only the current boundary.

## References

- `github/spec-kit` at `57cc518d63d6f10da3dd93df1ebcadda87c59374`
- `Egonex-AI/Understand-Anything` at `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`
- `addyosmani/agent-skills` at `06300e258ef62cdbfbc9b1615ac5b4f58bee05ac`
- `obra/superpowers` at `d884ae04edebef577e82ff7c4e143debd0bbec99`
- `Shubhamsaboo/awesome-llm-apps` at `41621a5735d573ce6d7d57def504fce873f18e4f`
