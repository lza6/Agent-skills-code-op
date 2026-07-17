# Codebase Structure

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `skills/production-delivery-orchestrator/` | 可安装技能产品：入口、客户端元数据、按需契约、兼容协议、安装器与安装测试 | `SKILL.md`; `agents/openai.yaml`; `references/`; `scripts/`; `tests/` |
| `evals/production-delivery-orchestrator/` | 离线评测、真实/合成 forward harness、跨 CLI matrix、fixture、测试、baseline 和报告 | `run_evals.py`; `run_forward_tests.py`; `run_client_matrix.py`; `cases.yaml`; `rubric.yaml` |
| `.github/workflows/` | 双系统 CI 门禁 | `.github/workflows/skill-evals.yml` |
| `docs/` | 项目识别、参考扫描和本次代码库事实文档 | `docs/project-benchmark-analysis.md`; `docs/reference-scan-report.md`; `docs/codebase/` |
| `reviews/` | 独立 Critic 六维审查和复验记录 | `reviews/final-critic.md` |
| `workflow_status.md` | 历史发布闭环和节点/风险/证据台账 | `workflow_status.md` |
| `README.md` | 产品定位、安装、兼容、安全边界、验证和发布说明 | `README.md` |

### 2) Entry Points

- Main runtime entry: `skills/production-delivery-orchestrator/SKILL.md`，由兼容 Agent Skills 的客户端读取。
- Secondary entry points:
  - 安装：`skills/production-delivery-orchestrator/scripts/install_skill.py`
  - 离线评测：`evals/production-delivery-orchestrator/run_evals.py`
  - forward-test：`evals/production-delivery-orchestrator/run_forward_tests.py`
  - CI：`.github/workflows/skill-evals.yml`
- How entry is selected: Agent 客户端按 frontmatter/显式调用选择技能；Python 工具由 CLI 命令和参数选择；CI 在 push/PR 触发。

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `SKILL.md` | 触发边界、授权分类、顶层状态机、按需 reference 路由 | 不应重复全部长协议或实现客户端专属工具调用 |
| `references/*.md` | discovery/outcome/planning/execution/validation/review/status 单一职责契约 | 不应默认全部加载；兼容长协议不能覆盖模块化契约优先级 |
| `scripts/install_skill.py` | 技能复制、目标预检、桥接受管区块、回滚式替换 | 不负责技能行为评测或远程发布 |
| `evals/run_evals.py` | 静态/行为代理评分、Git baseline、fixture 分析、报告 | 不应宣称真实 LLM 行为；不调用付费模型 |
| `evals/run_forward_tests.py` | 可选真实 Agent CLI 执行、fixture 隔离、脱敏、记录校验 | 未提供命令时不得伪造真实 forward PASS |
| `tests/` | 本地文件系统、哈希、脱敏、Schema、跨平台回归 | 不应修改真实用户目录或生产系统 |
| `reports/`, `docs/`, `reviews/` | 可追溯结果和限制披露 | 不应替代本轮实际运行证据 |

### 4) Naming and Organization Rules

- File naming pattern: Markdown 和目录主要使用 kebab-case；Python 模块使用 snake_case；测试为 `test_*.py`。
- Directory organization pattern: 以交付资产分区，而非传统 controller/service/repository 分层。
- Import aliasing or path conventions: Python 使用标准库绝对导入；仓库路径在报告中转换为 POSIX 相对路径或 `external:<label>`，避免暴露本机绝对路径。
- Generated-vs-source: `reports/` 是版本化证据产物；`__pycache__`、`.pyc`、`.DS_Store` 被安装和 artifact hash 排除。

### 5) Evidence

- `README.md`
- `skills/production-delivery-orchestrator/SKILL.md`
- `skills/production-delivery-orchestrator/references/`
- `skills/production-delivery-orchestrator/scripts/install_skill.py`
- `evals/production-delivery-orchestrator/`
- `.github/workflows/skill-evals.yml`
- `docs/codebase/.codebase-scan.txt`
