# Workflow Status

## 任务契约

- 目标：把 `production-delivery-orchestrator` 升级为轻量核心、按需加载、自动仓库侦察、风险驱动验证和多 Agent 审查闭环的通用软件交付技能，并发布到 `lza6/Agent-skills-code-op`。
- 复杂度：Deep
- 用户旅程：用户可用模糊自然语言描述问题；技能先扫描真实仓库并理解最终结果，在授权范围内自主实现、测试、续修、独立审查和复验；资深开发者的显式技术契约完整保留。
- MUST 验收标准：
  - 模糊故障先侦察仓库，再决定是否提问；
  - 修改类请求默认完成安全本地实现、测试、失败续修和相邻风险检查；
  - 核心 `SKILL.md` 轻量，长协议和专项契约按需加载；
  - Quick 不强制多 Agent、HTML、全量测试或工作流文件；
  - Deep/高风险任务使用 Builder、只读 Critic、主线程修复和原 Critic 复验；
  - 提供可执行离线 eval、真实安装演练、结构验证和基线对照；
  - README 全面中文说明 Codex、Claude Code 与通用 CLI 的真实安装/调用差异；
  - 独立 Critic 审查后 P0/P1 清零，再提交和推送。
- 允许范围：当前仓库内技能、references、安装器、README、eval 和工作流状态。
- 必须保留：已发布基线 `b3d9a17`、跨 CLI 兼容、用户现有未提交改动、安全和外部操作边界。
- 明确不做：不安装到用户全局目录，不部署生产，不调用付费服务，不宣称所有 CLI 都能原生自动发现，不泄露私密思维链。
- 审批边界：本地修改和验证已授权；用户已提供 GitHub 仓库并要求最终推送；生产、付费、破坏性和系统级安装不在范围内。
- 停止条件：全部 MUST 有新鲜证据、Critic `Approve`、P0/P1 为零并成功推送；或出现不可替代的权限/网络阻塞。

## 项目事实

- 技术与入口：单技能 Agent Skills 仓库；入口为 `skills/production-delivery-orchestrator/SKILL.md`，附 Python 安装器和 GitHub/npx 安装说明。
- 相关模块：`SKILL.md`、`references/`、`agents/openai.yaml`、`scripts/install_skill.py`、`evals/production-delivery-orchestrator/`、`README.md`。
- 工作区状态：基线 `b3d9a17`；当前有未提交候选改动，均属于本任务，尚未推送。
- 关键约束：核心渐进披露；同批 baseline/candidate 评测；只读 Critic；不把未执行检查写成通过。
- 重大假设及反转条件：当前仓库只发布一个技能；若安装器或 `npx skills` 真实行为与 README 不符，必须以运行结果修正文档。

## 节点看板

| ID | 节点目标 | 状态 | 依赖 | 文件/模块 | 验收标准 | 验证方式 | 证据引用 | 回滚 |
|---|---|---|---|---|---|---|---|---|
| N1 | 主仓库、参考技能和规则冲突审查 | passed | - | 全仓库、参考技能根目录 | 给出证据化 P0/P1/P2 与高价值参考 | 三个独立只读 Agent | Agent 审查回传 | 保留 `b3d9a17` |
| N2 | 轻量核心状态机与按需路由 | passed | N1 | `SKILL.md`、`openai.yaml`、长协议入口 | 默认不全文加载长协议；触发边界清晰 | 官方结构验证、字符量、eval | `SKILL.md` 轻量且默认上下文代理较基线下降 78.5% | 回退单组规则并复测 |
| N3 | 模块化发现、结果、计划、执行、验证、审查和状态契约 | passed | N1 | `references/` | 每个契约单一职责、中文、无 CLI 强绑定 | diff check、引用完整性、两次 forward-test | 八个按需 reference 均可解析 | 逐模块回退 |
| N4 | 可执行离线评测与视频任务 fixture | passed | N1 | `evals/production-delivery-orchestrator/` | 静态映射不冒充场景执行；真实 Git 基线；真实 forward-test 可追溯 | runner 自测、baseline/candidate、坏候选、forward harness/记录 | 静态状态为 COVERED/UNCOVERED；报告含 SHA-256；真实记录校验通过 | 保留 `cases.yaml` 与 Git 基线 |
| N5 | 跨 CLI 安装器与全面中文 README | passed | N2 | `README.md`、`install_skill.py`、安装测试、CI | 真实临时安装、重复保护、引用完整性和七类桥接通过 | 4 个 stdlib 集成测试；Windows/Linux CI 配置 | 实装、force、越界拒绝、不完整源和文件目标保护均通过 | 备份改名与恢复 |
| N6 | 主线程初步整合与验证 | passed | N2,N3 | 全仓库 | 结构、YAML、安装、eval、远程发现和两次 forward-test有实际证据 | 实际命令和退出码 | 初验完成；Critic 发现评测表述与 CI 覆盖缺口 | 按失败证据最小修复 |
| N7 | 独立 Critic 审查、主线程修复、原 Critic 复验 | passed | N6 | 当前 diff 与验证证据 | 六维审查通过，P0/P1 为零 | 独立只读 Agent | 原 Critic 复验 F1-F5 全部 Closed，Verdict Approve | 仅修复已确认问题 |
| N8 | 提交并推送 GitHub | passed | N7 | Git 历史与远程 | 提交成功、远程 main 可见 | git status/log/remote、远程发现、云端 CI | 功能提交 `0cf30f2` 已推送；Ubuntu/Windows CI 成功；npx 发现新 description | 不改写历史 |

## 风险与决策

| ID | 风险或决策 | 等级 | 依据 | 处理方式 | 状态 |
|---|---|---|---|---|---|
| R1 | 默认全文加载约 1,556 行长协议 | P0 | 与本地轻量 prompt 规则和渐进披露冲突 | 长协议降为显式/专项兼容层 | 已解决；默认上下文代理下降 78.5% |
| R2 | `description` 过宽并承载完整工作流 | P1 | 可能过度触发并让模型跳过正文 | 改为触发场景和负向边界 | 已解决；正负触发代理通过 |
| R3 | eval 只有 YAML 清单，无法执行 | P0 | 无 runner、rubric、fixture 和非零失败 | 建立离线 runner 与对照报告 | 已解决 |
| R4 | 桥接要求所有软件请求全文加载 | P0 | 污染项目上下文并冲突其他规则 | 改成轻量路由和按需加载 | 已解决 |
| R5 | 静态评测不能证明真实模型行为 | P1 | 结构合规不等于执行有效 | 静态映射改为 COVERED/UNCOVERED；增加真实记录和可配置 forward harness | 已解决，保留模型版本未知限制 |

## 验证台账

| ID | 关联节点/MUST | 实际验证 | 结果 | 变更标识/时间 | 新鲜度 | 剩余风险 |
|---|---|---|---|---|---|---|
| V1 | N1 | 三个 Agent 分别审查主仓库、13,018 个参考技能和规则/评测冲突 | passed | 本轮 | 新鲜 | 结论尚需实现验证 |
| V2 | N2,N3 | 官方 `quick_validate.py`、引用存在性、YAML 解析、`git diff --check` | passed | 本轮核心与契约改动后 | 新鲜 | Critic 修复后需重跑 |
| V3 | N2 | 真实 Git 基线对照：默认强制上下文代理下降 78.5% | passed | `b3d9a17` vs 当前候选 | 新鲜 | 字符量代理不是精确 tokenizer token |
| V4 | N4 | eval self-test、真实 Git baseline/candidate、坏候选非零、报告哈希一致性 | passed | 最终 runner/rubric/cases | 新鲜 | 离线静态映射不代表模型行为 |
| V5 | N5 | 4 个 TemporaryDirectory 真实安装集成测试；`--force`、七桥接、越界和不完整源 | passed | 最终安装器与测试 | 新鲜 | 云端 Windows/Linux CI 需推送后观察 |
| V6 | N3,N4 | 两个独立新上下文 forward-test；持久记录校验；harness synthetic self-test | passed | 本轮临时仓库与 `forward-tests.json` | 新鲜 | 精确模型/采样配置和原始工具 trace 不可见，已披露 |
| V7 | N2-N7 | 官方技能校验、4 项安装测试、forward self/record/NOT_RUN、eval self/candidate/known-bad、fixture RED、YAML/引用/报告一致性、diff/缓存检查 | passed | 最终候选工作树 | 新鲜 | 云端 CI 只能在推送后观察 |
| V8 | N8 | 远程 SHA、`npx skills --list`、GitHub Actions Ubuntu/Windows | passed | 功能提交 `0cf30f2` | 新鲜 | Actions: `29529506078`，两个矩阵任务均 success |

## 审查循环

| 轮次 | Critic 身份/降级方式 | Verdict | P0/P1 | Builder 修复 | 复验结果 |
|---|---|---|---|---|---|
| 预审 | 三个独立只读 Agent | Request Changes | P0: 默认长协议、不可执行 eval、过度桥接；P1: description、固定流程 | 已完成核心整改 | 进入正式 Critic |
| 1 | `/root/final_critic_2` | Request Changes | P0: 0；P1: F1 静态映射冒充场景、F2 CI 仅 dry-run、F3 状态滞后 | F1-F5 均已修复并取得新鲜证据 | 待原 Critic 复验 |
| 2 | `/root/final_critic_2` | Approve | P0: 0；P1: 0 | F1-F5 全部 Closed | 通过 |

## 外部等待项

无。

## 当前结论

- 当前阶段：完成。
- 已完成：轻量核心、八个模块化契约、全面中文 README、真实安装测试、真实 Git 基线 eval、两次独立新上下文 forward-test、两轮 Critic 和最终本地完成门。
- 当前主节点：无；全部节点已通过。
- 下一步：用户可通过仓库 URL、`npx skills` 或 Python 安装器安装使用。
- 未验证项：无阻塞项；不同客户端是否隐式自动调用仍取决于其版本和配置，README 已提供显式调用与桥接降级。
- 剩余边界：静态 eval 只能证明规则结构；真实 forward-test 仍受未暴露模型版本和临时 fixture 规模限制。
