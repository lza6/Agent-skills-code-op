# Codebase Concerns

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| medium | 真实 Agent 行为覆盖有限，多数 19-case 仅为静态 `COVERED/UNCOVERED` 代理 | `cases.yaml`; `run_evals.py:738`; `run_client_matrix.py`; `README.md` | 不能把离线 100 分外推为所有模型/客户端真实遵守 | matrix 已就绪；在专用环境中按客户端、版本和模型采集真实样本 |
| medium | `run_evals.py` 仍是大型多职责模块 | `run_evals.py` 的 artifact/routing/checks/report/fixture function inventory | 修改评分、hash 或报告时回归半径大 | 保持 CLI，按 golden report/CLI 契约逐步拆成 artifact/routing/checks/report/fixture 模块 |
| low/medium | 多目标安装已使用可补偿的跨目标事务；仍有检查与写入之间的理论 TOCTOU 窗口 | `InstallTransaction` journal/backup `install_skill.py:128-323`；begin/snapshot/apply/rollback `install_skill.py:772-793`；`test_multi_target_failure_restores_every_prior_target_and_bridge` | 进程外并发修改目标目录时，平台文件系统仍不能提供完全无竞态保证 | 保持现有预检、journal 与 rollback 回归；如未来威胁模型要求，再评估目录句柄/平台锁定方案 |
| low/medium | 兼容长协议与模块化契约存在重复维护面 | `SKILL.md`; `references/system-prompt.md` | 规则可能漂移或旧协议重新引入刚性行为 | 增加一致性/反向回归，长期缩小兼容层 |
| low/medium | 支持矩阵已机器可读，但客户端真实行为范围仍不完整 | `docs/support-matrix.json`；CI only Python 3.11；current-state CLI matrix | 用户能看到已测试范围，但不能把格式兼容误解为所有模型/客户端已验证 | 每次 CI runtime、CLI profile 或真实矩阵变化时更新 support matrix，并继续记录外部阻塞 |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|-----------------|---------------|
| Eval runner 单文件过大 | 功能在多轮加固中持续累积 | `evals/.../run_evals.py` | 维护和精确测试成本上升 | P2 小步提取纯函数模块，先锁定 golden report/CLI 契约 |
| 无覆盖率门禁 | 当前以行为测试和 known-bad 为主 | tests + CI | 新分支可能没有直接测试且不易量化 | 先对 Python 工具建立 branch coverage 基线，再决定阈值 |
| 固定 baseline `b3d9a17` | 用于持续与最初发布架构比较 | `run_evals.py:29` | 只能说明相对旧基线改进，不能证明对最近稳定版无退化 | 保留历史 baseline，同时增加 last-release baseline |
| 默认评测要求完整 Git 历史 | runner 从固定 commit 读取 baseline，CI 使用 `fetch-depth: 0` | `run_evals.py:29`; `.github/workflows/skill-evals.yml` | 浅克隆或 Source archive 中默认命令以 exit 2 停止 | 当前已提供清晰错误和显式 `--baseline`；P2 可考虑受控 release artifact baseline |
| 发布/支持元数据仍分散在 README/workflow/current-state | `docs/support-matrix.json` 已提供兼容 manifest，但发布叙述仍跨多个文档 | root docs | 文档漂移需要人工发现 | 继续以 current-state + support matrix 为源，并由一致性测试保护关键事实 |
| 历史状态文件很大且高 churn | 记录多轮发布和 Critic 证据 | `workflow_status.md` | 新任务难区分历史事实与当前状态 | 保留历史归档，顶部增加当前审计节点和明确版本边界 |

### 3) Security Concerns

| Risk | OWASP category (if applicable) | Evidence | Current mitigation | Gap |
|------|--------------------------------|----------|--------------------|-----|
| 项目级安装路径逃逸/链接竞态 | A01 Broken Access Control / local filesystem boundary | `resolve_project_path`; symlink tests | resolve + relative boundary、目标预检、已知链接攻击回归 | 检查与写入之间仍有理论 TOCTOU |
| Forward 输出泄露 Secret | A02 Cryptographic Failures / sensitive data exposure | secret regex + redaction tests | 命令、stdout/stderr、嵌套报告递归脱敏 | 自定义名称/编码格式不能保证全覆盖 |
| 外部 Agent 命令权限过宽 | N/A local process execution | `--agent-command`; 600s subprocess | 只有用户显式提供命令才运行；默认 NOT_RUN | harness 本身不提供 OS sandbox；依赖调用方边界 |
| 供应链与发布真实性 | A08 Software and Data Integrity Failures | pinned Actions; README checksum/provenance | Actions 固定 commit SHA；发布有 checksum/provenance 文档 | tag 未签名、Release 非 immutable、默认 `npx` CLI 版本可能漂移 |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| Deep 模式多 reference 上下文成本未做真实 token/延迟采样 | 只测 default-context char proxy | 默认上下文已降 76.7%，但 Deep 累积成本未知 | 更大仓库/更多契约时延迟与注意力成本增加 | 在真实 forward 中记录 token/time（客户端可提供时） |
| 参考/技能树完整 hash 每次扫描全部普通文件 | `sha256_path_tree`; `skill_artifact_files` | 当前技能很小，无明显症状 | 技能 artifact 显著增大时 I/O 线性增长 | 保持确定性，必要时缓存并绑定文件 metadata；先基准再改 |
| Eval runner 串行运行检查 | `evaluate_artifact` | 当前检查数量小 | 更大 rubric/case 集会延长 CI | 仅在基准证明需要时并行纯检查，保持报告顺序确定 |

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|-------------|----------------------|
| `workflow_status.md` | 混合历史、当前、发布与审查状态 | 最近 90 天 8 次变更，扫描最高 | 新节点追加且明确时间/版本，不回写旧证据含义 |
| `README.md` | 安装、发布、兼容和安全声明集中 | 6 次变更 | 每次行为变化同步命令实测、版本边界和限制 |
| `reviews/final-critic.md` | 历史 verdict 容易被误用为当前批准 | 5 次变更 | 新增审查轮次，旧 verdict 保留对应 commit/tag |
| `run_forward_tests.py` / reports | hash、脱敏、跨平台和证据新鲜度耦合 | 多轮发布持续变更 | 修改后重跑对应 forward/matrix suite、record verify、EOL/path cases |
| `install_skill.py` | 本地文件系统安全边界和替换恢复 | 4 次变更 | 真实 tempdir + symlink/junction + all-target 预检复验 |
| `run_evals.py` | 多职责且影响评分/报告/CI | 多轮发布持续变更 | 先锁定 current/known-bad/golden fingerprint，再小步重构 |

### 6) Open Decisions

1. P2：只有基准或回归痛点明确时，才拆分 `run_evals.py`；稳定 `v1.7.0` tag 不移动。
2. 要把格式兼容提升为真实行为兼容，仍需要专用 VM/容器或测试账号、客户端版本和可用模型/凭证；当前 Claude/Gemini 状态见 `docs/current-state.md`。
3. 当前机器可读范围只声明 CI 实测 Python 3.11；若要承诺更低版本、签名或 immutable Release 策略，需要新的发布决策和验证。

### 7) Intent vs. Reality

- README 的目标是跨 Codex、Claude Code 和通用 Agent Skills；当前真实行为 forward 证据主要来自 Codex，新客户端更多是格式、目录和桥接兼容证据。
- 产品名包含“生产级”，但仓库本身不是生产 Web/API 服务；数据库、缓存、队列、容器、APM 和业务部署均 N/A。
- `cases.yaml` 描述 19 个行为场景，但离线 runner 明确只证明静态规则可达；这与 README 的限制说明一致，不应解释为 19 个真实模型场景均通过。
- 仓库历史已完成并发布一轮与当前请求高度相似的改造；本轮是独立复核和下一阶段设计门，不应把历史 `Approve` 自动当成当前未审查修改的批准。

### 8) Evidence

- `docs/codebase/.codebase-scan.txt`
- `docs/project-benchmark-analysis.md`
- `docs/reference-scan-report.md`
- `reviews/final-critic.md`
- `workflow_status.md`
- `skills/production-delivery-orchestrator/scripts/install_skill.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `.github/workflows/skill-evals.yml`
