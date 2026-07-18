# 当前项目事实

> 更新于 2026-07-18；稳定发布 tag 解引用到 commit `80b416e`。本页是当前项目事实的唯一入口，不把 `main` HEAD 视为固定发布事实。

## 稳定发布

- 当前稳定安装来源是 [`v1.7.0`](https://github.com/lza6/Agent-skills-code-op/releases/tag/v1.7.0)，annotated tag 解引用到 `80b416ecd73d953dc0ead66c9996b142d21a7ecd`。
- README 的默认安装地址为 `tree/v1.7.0`；`main` 仅用于开发版/滚动版本，不替代稳定 tag。
- `v1.7.0` tag 内的 `release/metadata.json` 声明 `version: 1.7.0`、`tag: v1.7.0`，并指向本版本的 release note。

## Release 与供应链证明

- [main 双平台 skill-evals（29639353470）](https://github.com/lza6/Agent-skills-code-op/actions/runs/29639353470) 与 [tag release workflow（29639416337）](https://github.com/lza6/Agent-skills-code-op/actions/runs/29639416337) 均已成功；后者在两个 quality job 成功后创建 Release、attestation 和附件。
- Release 附件：[ZIP](https://github.com/lza6/Agent-skills-code-op/releases/download/v1.7.0/production-delivery-orchestrator-v1.7.0.zip)、[SHA256SUMS.txt](https://github.com/lza6/Agent-skills-code-op/releases/download/v1.7.0/SHA256SUMS.txt)、[provenance.json](https://github.com/lza6/Agent-skills-code-op/releases/download/v1.7.0/provenance.json)。ZIP SHA-256 为 `199f9fc66dd8739238c100588b3a1616838597ae5bd7cb0f41b724da6bf17c99`。
- 已执行的下载复验包括 checksum、`release/build_release.py --verify --expected-commit 80b416ecd73d953dc0ead66c9996b142d21a7ecd`、`gh attestation verify` 和 tagged `npx skills --list`。完整事实与命令结果见 [v1.7.0 release note](releases/v1.7.0.md)。

## 真实 CLI 矩阵

- R5：partial。Codex CLI `0.144.5`：新 hardened runner 的 `3/3 PASS`。
- Claude Code `2.1.212`：实际执行但本机 OAuth 账户没有可用模型；Gemini CLI `0.51.0`：未提供隔离 API/Vertex 凭证，未启动 Agent。两者都没有产生技能行为通过结论。
- 默认实跑仅接受仓库外的 `--agent-env-file`。已登录 Codex/Claude 如需使用本机 client config，必须同时显式传入 `--execute --allow-unsafe-host-execution --allow-host-client-config`；如需使用本机代理配置，还必须额外传入 `--allow-host-network-configuration`。此路径不复制凭证、不继承其他宿主环境；Gemini 没有 host-config fallback。
- 因此这不是跨客户端通过，也不是技能行为失败。完整边界和复跑条件见 [v1.7.0 release note](releases/v1.7.0.md)。

## Registry 当前范围

- [技能 registry](../skills/registry.json) 是由 `tools/build_skill_registry.py` 可重建的 schema=1 manifest；当前包含一个技能 `production-delivery-orchestrator`，并提供稳定的查询/漂移检查。它是未来多技能选择的兼容基础，不是 catalog 服务。
- `evals/production-delivery-orchestrator/client-profiles.json` 是独立的 CLI profile 配置：当前覆盖 Codex CLI、Claude Code、Gemini CLI 三个命令模板，Windows 使用 `.cmd`，Linux/macOS 使用无后缀命令。默认隔离执行时三者均要求通过仓库外 `--agent-env-file` 提供各自认证（Codex `OPENAI_API_KEY`、Claude `ANTHROPIC_API_KEY`、Gemini API key 或 Vertex 集）。对于已登录的 Codex/Claude，另有三重显式 opt-in 的 `--execute --allow-unsafe-host-execution --allow-host-client-config` 路径：它只向该 Agent 暴露对应 CLI 配置根目录，不复制凭证、不继承宿主环境，也不把路径写入报告；Claude 仅在该分支移除会排斥 OAuth 的 `--bare`。Gemini 没有 host-config fallback，临时 fixture 使用 `--skip-trust` 而不继承宿主 trust。它记录可调用命令、认证契约和版本匹配边界，不证明任一客户端已通过真实行为矩阵。

## 边界

- `80b416e` 是 release tag 的提交；后续 `main` 文档更新不移动该 tag。
- `workflow_status.md` 顶部的当前 v1.7.0 发布闭环与本页交叉校验；其后的台账、历史审计和历史 release 说明不是本页的 current-state。
