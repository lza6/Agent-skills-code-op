# Consumer Command Contract

## Installer help

- **Consumer**: a user invoking `install_skill.py --help` on Windows or Linux.
- **Guarantee**: human-readable UTF-8 Chinese help and normal command completion on a stream that
  allows configuration.
- **Boundary**: an embedded/detached stream that rejects reconfiguration remains supported; the
  command must not crash solely because stream configuration is unavailable.

## Default evaluation baseline

- **Consumer**: a maintainer invoking `run_evals.py` without `--baseline`.
- **Prerequisite**: the current Git repository resolves the declared baseline ref and skill path.
- **Failure behavior**: before evaluation, exit nonzero with a concise message that names the
  unavailable ref, explains shallow/source-archive cause and shows `--baseline <path>` or a
  history-fetch recovery route.
- **Recovery behavior**: a valid explicit baseline path continues through the existing evaluator
  unchanged; known-bad candidates retain their expected nonzero result.

## Documentation fact boundary

- **Consumer**: a maintainer reading current-state, codebase and review documents.
- **Guarantee**: current documents do not contradict executable transaction/release behavior;
  historical materials expose an explicit time boundary.
- **Failure behavior**: a consistency test fails before merge if a protected fact is removed or
  inverted.
