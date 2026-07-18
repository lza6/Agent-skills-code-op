# Quickstart: Validate the Production Audit Feature

## Prerequisites

- Python 3.11 and Git.
- A checkout with the repository's Git history for default evaluation, or an explicit valid
  baseline directory for restricted checkouts.
- Windows tests should use `cmd.exe` or no-profile PowerShell on hosts whose PowerShell profile
  is broken.

## Validation sequence

1. Run installer tests and the installer help command. Confirm Chinese help text is readable.
2. Run evaluator tests, including the missing-history preflight regression.
3. Run workflow current-state tests and generated registry/dependency checks.
4. Build and verify a local release artifact; do not compare its byte hash with a remote release
   asset unless deterministic packaging is separately guaranteed.
5. Open the HTML report from disk, complete the quiz and confirm immediate feedback.
6. Request an independent read-only six-dimension review. Only then commit/push and wait for
   remote dual-platform quality.

## External capability boundary

Understand Anything may be installed and structurally inspected without creating a graph. Graph
generation requires a configured model/provider and can consume tokens; run it only in the
controlled repository copy after reviewing its generated file set. Claude/Gemini real-client
matrix validation remains blocked until controlled model access is available.
