# External Integrations

## Core Sections (Required)

### 1) Integration Inventory

| System | Type (API/DB/Queue/etc) | Purpose | Auth model | Criticality | Evidence |
|--------|---------------------------|---------|------------|-------------|----------|
| Local filesystem | File system | 安装技能、更新桥接、创建临时 fixture、写报告 | 当前 OS 用户权限 | high | `install_skill.py`; `run_forward_tests.py` |
| Git CLI/repository | Process/VCS | 读取固定 baseline、初始化 fixture、检查 status/diff/commit | 本地仓库权限；不需要远程凭证 | high | `run_evals.py`; `run_forward_tests.py` |
| Agent/CLI command | External process | 可选执行真实 forward-test | 由用户提供的命令/客户端自行处理凭证 | medium/high | `run_forward_tests.py --agent-command` |
| GitHub Actions | CI | Ubuntu/Windows 重复验证 | GitHub 仓库权限；workflow 仅 `contents: read` | high | `.github/workflows/skill-evals.yml` |
| `npx skills` / Agent Skills clients | Distribution/consumer tooling | 安装、发现和使用技能 | 由消费者环境决定 | medium | `README.md` |

仓库运行代码没有数据库、缓存、消息队列、业务 HTTP API、OAuth 或支付集成。

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| Versioned JSON/Markdown reports | 保存离线 eval 与 forward 证据 | Python `pathlib`/`json` | 记录陈旧、敏感输出或绝对路径泄露 | `evals/.../reports/`; two runners |
| Git history/tags | baseline 与发布边界 | `git show`, `git ls-tree`、人工发布记录、README/workflow 状态证据 | baseline 固定、远程状态与本地声明可能漂移；浅克隆缺少默认 baseline | `run_evals.py`; `README.md`; `workflow_status.md` |
| Local target directories | 安装后的技能与项目桥接 | `install_skill.py` | 覆盖、symlink/junction 逃逸、部分安装 | installer + tests |

### 3) Secrets and Credentials Handling

- Credential sources: 仓库代码不读取必需 Secret；真实 Agent CLI 的凭证由外部客户端环境管理。
- Hardcoding checks: 未发现提交的 `.env` 模板或业务凭证；forward harness 包含常见 Secret 模式脱敏回归。
- Rotation or lifecycle notes: N/A；项目不管理凭证生命周期。
- Known limitation: 脱敏是启发式规则，无法保证识别所有自定义 Secret 名称和格式。

### 4) Reliability and Failure Behavior

- Retry/backoff behavior: 没有自动重试外部 Agent CLI；技能契约要求基于新证据续修，但 harness 单次 case 不重试。
- Timeout policy: 真实 Agent case 的 subprocess timeout 固定为 600 秒，timeout 转成结构化失败并脱敏。
- Circuit-breaker or fallback behavior: 无 circuit breaker；未提供 `--agent-command` 时明确 `NOT_RUN` 并退出 `2`；离线 eval 不依赖网络模型。
- Filesystem rollback: 单目标替换使用 staging/backup/rename 及异常恢复；跨多个目标不是全局事务。
- Git history failure: 默认 offline eval 需要提交 `b3d9a17`；CI 通过 `fetch-depth: 0` 获取完整历史，浅克隆/源码归档必须改用显式 `--baseline`。

### 5) Observability for Integrations

- Logging around external calls: Git/Agent subprocess 捕获 exit code、stdout/stderr；forward 报告持久化经脱敏的命令与结果。
- Metrics/tracing coverage: 无 APM/metrics/tracing；对短命 CLI 以结构化报告、hash 和退出码作为审计信号。
- Missing visibility gaps: 真实 Agent 记录不包含协作运行时未暴露的精确模型、采样参数和完整工具 trace；其他客户端行为矩阵未执行。

### 6) Evidence

- `skills/production-delivery-orchestrator/scripts/install_skill.py`
- `skills/production-delivery-orchestrator/tests/test_install_skill.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `evals/production-delivery-orchestrator/reports/forward-tests.json`
- `.github/workflows/skill-evals.yml`
- `README.md`
