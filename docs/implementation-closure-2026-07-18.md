# P0/P1 实施闭环报告（2026-07-18）

> **范围与基线。** 本报告记录基线 `eb3bf18` 上的本地 P0/P1 实现闭环；未创建 commit、tag 或 GitHub Release，未执行真实付费/订阅 Agent CLI。它补充而不改写 [当前对标报告](project-benchmark-revalidation-2026-07-18.md) 的问题与路线图。

## 已完成的代码交付

| 节点 | 实现 | 关键负向验收 | 兼容性/回滚 |
|---|---|---|---|
| I1 Release 质量前置 | `release.yml` 在同一 workflow 增加 Ubuntu/Windows `quality` matrix；`publish` 仅在 `needs: quality` 成功后构建、attest、发布。默认 token 降为只读，仅 publish 获写权限。 | workflow governance 测试验证同工作流依赖、最小权限和 Actions 完整 SHA 固定。 | 不改变技能 CLI 或已发布 tag；回滚仅回退 workflow 提交，绝不移动历史 tag。 |
| I1 CI 差异与治理 | `skill-evals.yml` 与 Release quality job 按 PR base/head、push before/head 检查 whitespace；首个 push/tag 有明确 fallback。新增 stdlib governance/已知凭据模式测试。 | 不再在干净 checkout 执行无效的裸 `git diff --check`。 | 治理测试不替代 gitleaks/CodeQL/SBOM 等专用工具；它是零新增运行时依赖的基础门。 |
| I2 forward 资源边界 | 外部 Agent 执行改为 Windows Job Object、Linux subreaper + process-group（其他 POSIX 仅 process-group）收敛；stdout/stderr 共用 256 KiB 上限并持续排空，超限 fail-closed，报告加入 `output_capture`/`resource_failure`。 | Windows 安全 stub 验证 timeout、持管道孤儿和关闭管道孤儿均被清理；Ubuntu WSL 实测 `setsid` 脱组孤儿也被 subreaper 清理；超量输出不会保留 secret。 | 原有 CLI 参数和 `CompletedProcess` 调用形态保持；新增报告字段为可选字段。 |
| I2 报告路径边界 | 三个 CLI 和实际写报告点都只接受 portable filename prefix，拒绝绝对路径、分隔符、`..`。 | `../escape`、Windows 路径、嵌套路径均在启动 Agent/写文件前失败。 | 正常的字母数字、`.`、`_`、`-` 前缀兼容；非法历史自动化调用会得到明确非零错误。 |
| I3 ZIP 验证资源边界 | 验证前限制 1,000 成员、16 MiB/成员、64 MiB 总未压缩、100:1 压缩比；以 128 KiB 分块读取、二次计数和流式 raw SHA 代替无界 `archive.read()`。 | 即使攻击者重写 `SHA256SUMS.txt`，成员数、单成员、总量和压缩比越限仍 fail-closed。 | 正常 v1.5.0 制品/provenance canonical digest 保持兼容；阈值为模块常量，可在后续版本审计调整。 |

## 新鲜本地验证

| 验证 | 结果 |
|---|---|
| workflow governance | 6/6 PASS |
| installer/inventory | 25/25 PASS |
| eval/forward/client matrix | Windows：49 项，47 PASS、2 Linux subreaper 专用回归 skip；Ubuntu WSL：两条 Linux 专用回归 2/2 PASS |
| release builder | 7/7 PASS |
| offline eval self-test | PASS，`llm_calls: 0` |
| forward synthetic self-test | PASS；明确不是实际 Agent 行为 |
| candidate eval | baseline `31.2` → candidate `100.0`，delta `68.8` |
| known-bad | candidate `12.3`，按预期 exit `1` 被拒绝 |
| release build + verify | 本地构建并验证 `v1.5.0` 制品 PASS |
| Python compile / whitespace | PASS |

## 尚未伪装为通过的外部完成门

1. 推送后必须由 GitHub Actions 在真实 Ubuntu/Windows runner 执行 `quality`，并由 tag workflow 证明 `publish` 仅在 quality 成功后运行。
2. 真正发布后需下载资产，复验 checksum、provenance 和 `gh attestation verify`；本轮没有创建 Release。
3. 真实 Codex/Claude/Gemini 样本需要专用隔离环境、明确费用/配额和最小凭据；本轮只运行安全 local stub 与 synthetic harness。
4. 正式覆盖率阈值、专用 secret/SBOM/依赖扫描和多技能 registry 仍属 P2 治理工作；没有被表述为已完成。

## 独立审查要求

在任何 commit/push/tag 前，独立只读 Critic 必须从需求完整性、逻辑正确性、边界、代码质量、测试覆盖和实际运行六维审查本次 diff。发现的 P0/P1 仅由主线程最小修复，再由同一 Critic 复验。

本轮最终 Critic 已复验通过：P0/P1 均为 0；其先后发现的 POSIX 脱组 child、脱组 grandchild、matrix suffix prefix 上限和 Windows 文档表述均已修复并复验。
