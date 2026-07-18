# 当前项目事实

> 更新于 2026-07-18；发布后文档锚点为 commit `290bdc4`。本页是当前项目事实的唯一入口，不把 `main` HEAD 视为固定发布事实。

## 稳定发布

- 当前稳定安装来源是 [`v1.6.0`](https://github.com/lza6/Agent-skills-code-op/releases/tag/v1.6.0)，annotated tag 解引用到 `3471adadb142d884e6f566f846f4913649bc88e0`。
- README 的默认安装地址保持 `tree/v1.6.0`；`main` 仅用于开发版/滚动版本，不替代稳定 tag。
- `v1.6.0` tag 内的 `release/metadata.json` 声明 `version: 1.6.0`、`tag: v1.6.0`，并指向本版本的 release note。当前工作树的 metadata 是尚未发布的 `v1.7.0` 候选；在其 tag、Release 和发布后复验均完成前，不替代稳定安装来源。

## Release 与供应链证明

- [main 双平台 skill-evals（29631900219）](https://github.com/lza6/Agent-skills-code-op/actions/runs/29631900219) 与 [tag release workflow（29632189527）](https://github.com/lza6/Agent-skills-code-op/actions/runs/29632189527) 均已成功；后者创建 Release。
- 发布后文档验证的 [main skill-evals（29632673102）](https://github.com/lza6/Agent-skills-code-op/actions/runs/29632673102) 也成功，绑定 `290bdc4`。
- Release 附件：[ZIP](https://github.com/lza6/Agent-skills-code-op/releases/download/v1.6.0/production-delivery-orchestrator-v1.6.0.zip)、[SHA256SUMS.txt](https://github.com/lza6/Agent-skills-code-op/releases/download/v1.6.0/SHA256SUMS.txt)、[provenance.json](https://github.com/lza6/Agent-skills-code-op/releases/download/v1.6.0/provenance.json)。ZIP SHA-256 为 `199f9fc66dd8739238c100588b3a1616838597ae5bd7cb0f41b724da6bf17c99`。
- 已执行的下载复验包括 checksum、`release/build_release.py --verify --expected-commit 3471adadb142d884e6f566f846f4913649bc88e0`、`gh attestation verify` 和 tagged `npx skills --list`。完整事实与命令结果见 [v1.6.0 release note](releases/v1.6.0.md)。

## 真实 CLI 矩阵

- R5：partial。Codex CLI `0.144.5`：`3/3 PASS`。
- Claude Code `2.1.212`：凭证缺失（隔离环境未登录）；Gemini CLI `0.51.0`：凭证缺失（未提供认证变量）。两者都没有产生技能行为结论。
- 因此这不是跨客户端通过，也不是技能行为失败。重跑条件和脱敏逐案例结果见 [真实 CLI 矩阵证据](releases/evidence/v1.6.0-real-cli-matrix.md)。

## Registry 当前范围

- [技能 registry](../skills/registry.json) 是由 `tools/build_skill_registry.py` 可重建的 schema=1 manifest；当前包含一个技能 `production-delivery-orchestrator`，并提供稳定的查询/漂移检查。它是未来多技能选择的兼容基础，不是 catalog 服务。
- `evals/production-delivery-orchestrator/client-profiles.json` 是独立的 CLI profile 配置：当前覆盖 Codex CLI、Claude Code、Gemini CLI 三个命令模板，Windows 使用 `.cmd`，Linux/macOS 使用无后缀命令。默认隔离执行时三者均要求通过仓库外 `--agent-env-file` 提供各自认证（Codex `OPENAI_API_KEY`、Claude `ANTHROPIC_API_KEY`、Gemini API key 或 Vertex 集）。对于已登录的 Codex/Claude，另有三重显式 opt-in 的 `--execute --allow-unsafe-host-execution --allow-host-client-config` 路径：它只向该 Agent 暴露对应 CLI 配置根目录，不复制凭证、不继承宿主环境，也不把路径写入报告；Claude 仅在该分支移除会排斥 OAuth 的 `--bare`。Gemini 没有 host-config fallback，临时 fixture 使用 `--skip-trust` 而不继承宿主 trust。它记录可调用命令、认证契约和版本匹配边界，不证明任一客户端已通过真实行为矩阵。

## 边界

- `290bdc4` 是发布后文档更新锚点，不是 release tag 的提交，也不承诺后续 `main` 不会前进。
- `workflow_status.md` 顶部的当前 v1.6.0 发布闭环与本页交叉校验；其后的台账、历史审计和历史 release 说明不是本页的 current-state。
