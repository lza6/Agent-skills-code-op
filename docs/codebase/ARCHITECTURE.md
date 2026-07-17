# Architecture

## Core Sections (Required)

### 1) Architectural Style

- Primary style: 文档驱动的状态机 + 渐进披露路由 + 本地 CLI 工具/评测适配器。
- Why this classification: `SKILL.md` 明确以 `DISCOVER → ALIGN → PLAN → EXECUTE → VALIDATE → REVIEW → CLOSE` 推进，并按状态选择 reference；Python 工具围绕安装、baseline 评测和 forward 验证提供边界适配。
- Primary constraints:
  1. 必须跨 Codex、Claude Code 和通用 Agent Skills 客户端保持低耦合；
  2. 默认上下文必须轻量，不能每次加载 1,560 行兼容长协议；
  3. 本地修改、生产/付费/远程操作的授权边界必须分离；
  4. 静态规则代理不能冒充真实 Agent 行为证据。

### 2) System Flow

```text
用户请求/客户端发现
  -> SKILL.md 触发与授权分类
  -> 按状态读取必要 contract
  -> Agent 在目标仓库发现/对齐/计划/执行
  -> 风险驱动验证
  -> 独立 Critic 与复验（适用时）
  -> 证据闭环或真实阻塞
```

配套工具流：

```text
技能源目录
  -> install_skill.py 全量预检
  -> staging copy
  -> 可选旧目录 backup
  -> 同目录顺序 rename / 失败补偿恢复
  -> 原生技能目录和受管桥接文件
```

```text
Git baseline + 当前 candidate + rubric + cases + fixture
  -> run_evals.py 加载可达契约
  -> 静态/行为代理检查与 tree fingerprint
  -> PASS/FAIL JSON + Markdown 报告
```

```text
隔离 fixture + 显式 Agent CLI 命令
  -> run_forward_tests.py 执行修改/只读案例
  -> 测试、git status、diff、输出脱敏
  -> artifact-bound record
  -> verify-record 新鲜度校验
```

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| Skill core | 顶层策略、状态转换、授权和 reference 路由 | 具体客户端实现与完整专项细节 | `skills/.../SKILL.md` |
| Contracts | 单阶段规则、验收、失败与停止条件 | 无条件全量加载 | `skills/.../references/*.md` |
| Installer adapter | 文件系统目标、预检、桥接、替换恢复 | 远程下载、发布或行为评测 | `scripts/install_skill.py` |
| Offline evaluator | baseline/candidate、静态能力代理、fixture、报告指纹 | 真实模型执行结论 | `evals/.../run_evals.py`; `rubric.yaml` |
| Forward harness | 隔离执行、真实命令适配、脱敏、记录验证 | 未运行时的伪 PASS | `evals/.../run_forward_tests.py` |
| CI | 跨平台重复验证和 known-bad 阻断 | 生产部署 | `.github/workflows/skill-evals.yml` |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| State machine | `SKILL.md` | 让复杂任务有明确阶段和停止门 |
| Progressive disclosure/router | `SKILL.md` + `references/` | 降低默认上下文和规则冲突 |
| Preflight + staging + backup | `install_skill.py` | 通过同目录替换与失败补偿降低覆盖、部分替换和损坏风险；不宣称跨平台原子事务 |
| Managed block | `install_skill.py` | 幂等更新项目规则且保留用户内容 |
| Canonical tree hashing | `run_evals.py`; `run_forward_tests.py` | 跨平台绑定完整 artifact 与证据新鲜度 |
| Adapter/harness | `run_forward_tests.py` | 将任意显式 Agent CLI 命令接入统一验收 |
| Builder/Critic separation | `review-contract.md` | 防止实现者自我签收 |

### 5) Known Architectural Risks

- `run_evals.py` 为 1,146 行单文件，混合 artifact、路由、rubric、fixture、报告和 CLI；维护和单元隔离成本偏高。
- 1,560 行 `system-prompt.md` 与模块化契约形成双维护面；优先级已声明，但内容漂移仍需评测防护。
- 安装器会先对全部目标预检，但多个目标的真实复制不是跨目标单事务；后续目标失败时，前面已成功目标可能保留。
- 路径检查与后续文件操作之间存在理论 TOCTOU 窗口；当前测试覆盖已知 symlink/junction 逃逸，但未使用平台目录句柄彻底消除竞态。
- 19 个案例多数是静态覆盖映射；真实行为证据只有有限、历史记录的 Agent 场景，且未覆盖全部客户端。

### 6) Evidence

- `skills/production-delivery-orchestrator/SKILL.md`
- `skills/production-delivery-orchestrator/references/system-prompt.md`
- `skills/production-delivery-orchestrator/references/review-contract.md`
- `skills/production-delivery-orchestrator/scripts/install_skill.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `.github/workflows/skill-evals.yml`
