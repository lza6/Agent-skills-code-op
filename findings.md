# Findings and Decisions

## Requirements

- Install or verify the requested planning, testing, security, CI, frontend, MCP, review and
  reusable-skill capabilities without inventing availability.
- Use Spec Kit before implementation; persist a requirements trace, plan, tasks and evidence.
- Audit the whole repository as a production deliverable, then fix verified defects and update
  documentation, tests and a human-readable HTML handoff with a quiz.
- Use independent read-only review and re-review after fixes.
- Keep real external Agent execution, credentials and production claims honest.

## Research Findings

- This is a Python 3.11 standard-library Agent Skill distribution, installer, evaluator and
  release repository; it has no frontend, backend API, database, container or SaaS runtime.
- The actual user journey is discovery/install → routed skill → offline evaluation or optional
  isolated real CLI → dual-platform quality → release proof.
- v1.7.0 release R1–R4 are verified; real CLI matrix R5 remains partial: Codex is 3/3 PASS,
  Claude has no usable model and Gemini has no isolated credentials.
- Local skill roots already contain all requested exact skills except `composio-connect`.
  `specify 0.12.16` is installed. `gemini` exists on PATH but its help/version output did not
  prove functional execution.
- Confirmed P1: `docs/codebase/CONCERNS.md` says there is no global multi-target transaction,
  contradicting the installer, README and current tests.
- Confirmed P2: Windows `cmd` renders Chinese installer help incorrectly; default eval needs
  full Git history; historical review headings can be mistaken for current v1.7 facts.
- Spec Kit analysis found no constitution violation or uncovered functional requirement. It did
  require an actual `001-production-audit` branch, a real browser journey for the HTML quiz and
  explicit per-skill invocation evidence; those corrections are now present in `tasks.md`.

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Use pinned upstream sources for any new external installation | Floating GitHub main and deprecated catalogs are not sufficient supply-chain evidence. |
| Validate capabilities by scope rather than force every one on this repository | Figma, frontend and MCP authoring are not currently applicable; their local presence is verified, not misrepresented as project work. |
| Treat an Understand Anything graph as navigation evidence only | Its LLM summaries/graph do not prove behavior, security or release correctness. |
| Prefer explicit preflight failure for shallow history over hidden fallback | Baseline comparison must never silently compare against the wrong artifact. |
| Use `001-production-audit` as the change branch | The Spec Kit feature and Git state now agree; v1.7.0 remains immutable. |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| The official OpenAI skills catalog is deprecated | Reuse already-installed curated skills and record source/version; do not introduce it as a floating new dependency. |
| Understand Anything requires model/provider access to generate a graph | Inspect installer first, use a scoped temporary/copy installation, and record an external stop condition if no safe model execution path exists. |
| Composio is an SDK with OAuth and API-key authority, not the requested standalone skill | Do not install or configure it for an unrelated repository. |

## Resources

- `docs/current-state.md`, `workflow_status.md`, `README.md`
- `https://github.com/github/spec-kit` at `57cc518d63d6f10da3dd93df1ebcadda87c59374`
- `https://github.com/Egonex-AI/Understand-Anything` at `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`
- `https://github.com/addyosmani/agent-skills` at `06300e258ef62cdbfbc9b1615ac5b4f58bee05ac`
- `https://github.com/obra/superpowers` at `d884ae04edebef577e82ff7c4e143debd0bbec99`

## Visual and Browser Findings

- Understand Anything provides a local graph/dashboard after generation, but generation can
  consume model tokens. Its viewer is read-only only after a graph already exists.

## Final Audit Findings Before Independent Review

- The repository is not a SaaS product. UI/API/database/queue/container/SQL stress tests are
  `not_applicable`, while installer, archive, Git history, subprocess, credentials and release
  provenance are the actual production boundary.
- The final browser evidence is real: a local HTTP server plus headless Playwright verified the
  HTML quiz's failing score, passing score and reset state. It is a report journey, not a product
  E2E claim.
- The independent tool audit found a Windows Unicode bug in the locally installed `gh-fix-ci`
  helper: `git rev-parse` output was locale-decoded before being used as a cwd. UTF-8 decoding
  fixed the helper; the current branch simply has no PR to inspect.
- The report browser test itself first contained a bad test setup (four correct selections while
  expecting three). The browser caught it; the fixture now deliberately makes 3/5 fail before
  changing one answer to 4/5 pass.
- `pr-review` produced zero errors and two non-blocking warnings for optional frontmatter fields.
  They conflict with the repository's Skill-Creator-compatible `name`/`description` only shape,
  so they are documented rather than cargo-culted into the public contract.
