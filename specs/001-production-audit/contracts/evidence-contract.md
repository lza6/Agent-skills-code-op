# Evidence Contract

| Evidence type | Supports | Does not support |
|---|---|---|
| Unit/integration test | The exercised code path and asserted boundary | A real hosted Agent/model outcome |
| Offline evaluator | Static/routed contract coverage and fixture behavior | Prompt execution or all-client compatibility |
| CLI probe | Command discoverability/version response | Successful model invocation |
| Hardened real CLI fixture | The recorded client, fixture and cases | Other clients, credentials, models or future artifacts |
| Release artifact checksum/attestation | Exact release asset provenance/integrity | Later main-branch documentation changes |
| Understand Anything graph | Repository navigation and structural exploration | Code correctness, security, performance or release acceptance |

Every report must state the narrow evidence type and its invalidation condition.
