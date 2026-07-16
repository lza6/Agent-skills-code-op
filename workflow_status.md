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
- 工作区状态：远程 `main` 为 `b3fffeb`；本地 `d6476d7` 已修复首次最终推送暴露的跨平台问题，状态文档待提交再推送。
- 关键约束：核心渐进披露；同批 baseline/candidate 评测；只读 Critic；不把未执行检查写成通过。
- 重大假设及反转条件：当前仓库只发布一个技能；若安装器或 `npx skills` 真实行为与 README 不符，必须以运行结果修正文档。

## 节点看板

| ID | 节点目标 | 状态 | 依赖 | 文件/模块 | 验收标准 | 验证方式 | 证据引用 | 回滚 |
|---|---|---|---|---|---|---|---|---|
| N1 | 主仓库、参考技能和规则冲突审查 | passed | - | 全仓库、参考技能根目录 | 给出证据化 P0/P1/P2 与高价值参考 | 三个独立只读 Agent | Agent 审查回传 | 保留 `b3d9a17` |
| N2 | 轻量核心状态机与按需路由 | passed | N1 | `SKILL.md`、`openai.yaml`、长协议入口 | 默认不全文加载长协议；触发边界清晰 | 官方结构验证、字符量、eval | `SKILL.md` 轻量且当前默认上下文代理较基线下降 77.2% | 回退单组规则并复测 |
| N3 | 模块化发现、结果、计划、执行、验证、审查和状态契约 | passed | N1 | `references/` | 每个契约单一职责、中文、无 CLI 强绑定 | diff check、引用完整性、两次 forward-test | 八个按需 reference 均可解析 | 逐模块回退 |
| N4 | 可执行离线评测与视频任务 fixture | passed | N1 | `evals/production-delivery-orchestrator/` | 静态映射不冒充场景执行；真实 Git 基线；真实 forward-test 可追溯 | runner 自测、baseline/candidate、坏候选、forward harness/记录 | 静态状态为 COVERED/UNCOVERED；报告含 SHA-256；真实记录校验通过 | 保留 `cases.yaml` 与 Git 基线 |
| N5 | 跨 CLI 安装器与全面中文 README | passed | N2 | `README.md`、`install_skill.py`、安装测试、CI | 真实临时安装、重复保护、引用完整性和七类桥接通过 | 4 个 stdlib 集成测试；Windows/Linux CI 配置 | 实装、force、越界拒绝、不完整源和文件目标保护均通过 | 备份改名与恢复 |
| N6 | 主线程初步整合与验证 | passed | N2,N3 | 全仓库 | 结构、YAML、安装、eval、远程发现和两次 forward-test有实际证据 | 实际命令和退出码 | 初验完成；Critic 发现评测表述与 CI 覆盖缺口 | 按失败证据最小修复 |
| N7 | 独立 Critic 审查、主线程修复、原 Critic 复验 | passed | N6 | 当前 diff 与验证证据 | 六维审查通过，P0/P1 为零 | 独立只读 Agent | 原 Critic 复验 F1-F5 全部 Closed，Verdict Approve | 仅修复已确认问题 |
| N8 | 提交并推送 GitHub | passed | N7 | Git 历史与远程 | 提交成功、远程 main 可见 | git status/log/remote、远程发现、云端 CI | 功能提交 `0cf30f2` 已推送；Ubuntu/Windows CI 成功；npx 发现新 description | 不改写历史 |
| N9 | 严格 1–9 项目识别与参考对标报告 | passed | N8 | `docs/` | 主项目、参考筛选、差距、迁移、路线图、实施和未知项均有证据 | 文档结构、路径和需求矩阵检查 | `docs/project-benchmark-analysis.md`、`docs/reference-scan-report.md` | 删除本批文档 |
| N10 | 安装器与 forward/eval 证据安全加固 | passed | N9 | installer、forward、eval、tests、CI | symlink 不越界、报告脱敏、记录强校验、legacy 不代打 | 8 项安装测试、6 项 forward 测试、eval 三类 self-test | 主线程统一验证通过；提交 `000ff40` | 回退提交 `000ff40` |
| N11 | 持久化独立 Critic、修复复验和再次发布 | in_progress | N10 | `reviews/`、README、workflow、GitHub | 六维审查 P0/P1 为零，远程和双 OS CI 成功 | 同一 Critic 复验、Git/Actions/npx | R12/R13 已由原 Critic 复验 Closed；等待再次推送和双 OS CI | 不改写历史 |

## 风险与决策

| ID | 风险或决策 | 等级 | 依据 | 处理方式 | 状态 |
|---|---|---|---|---|---|
| R1 | 默认全文加载约 1,556 行长协议 | P0 | 与本地轻量 prompt 规则和渐进披露冲突 | 长协议降为显式/专项兼容层 | 已解决；当前默认上下文代理下降 77.2% |
| R2 | `description` 过宽并承载完整工作流 | P1 | 可能过度触发并让模型跳过正文 | 改为触发场景和负向边界 | 已解决；正负触发代理通过 |
| R3 | eval 只有 YAML 清单，无法执行 | P0 | 无 runner、rubric、fixture 和非零失败 | 建立离线 runner 与对照报告 | 已解决 |
| R4 | 桥接要求所有软件请求全文加载 | P0 | 污染项目上下文并冲突其他规则 | 改成轻量路由和按需加载 | 已解决 |
| R5 | 静态评测不能证明真实模型行为 | P1 | 结构合规不等于执行有效 | 静态映射改为 COVERED/UNCOVERED；增加真实记录和可配置 forward harness | 已解决，保留模型版本未知限制 |
| R6 | 目标要求的 1–9 分析未持久化 | P0 | 既有 README/workflow 不能替代完整对标输出 | 新增项目分析和参考扫描报告 | 已解决，待 Critic |
| R7 | 标准桥接可经 symlink 写出项目边界 | P1 | 标准路径未统一安全解析 | 标准/custom bridge 统一 resolve + 回归测试 | 已解决；最终套件通过 |
| R8 | Forward 报告可能泄露 Secret，记录校验过弱 | P1 | command/stdout/stderr 原样持久化 | 递归脱敏、固定 case Schema、timeout 结构化 | 已解决；10 项测试通过 |
| R9 | 静态 capability 可能由默认不可达 legacy 代打 | P2 | capability 曾扫描全部 references | 使用 routed capability text；baseline 强制 legacy 例外 | 已解决；candidate 强制 legacy 为 0 |
| R10 | 项目级 native 技能安装可经父目录 symlink/junction 越界 | P1 | Critic 临时目录复现：exit 0，项目外创建技能 | 解析后边界校验；normal/force/dry-run/all/user 回归 | 已解决；原攻击重放 exit 1 |
| R11 | Forward 记录只绑定 `SKILL.md`，routed reference 变化后仍 PASS | P1 | Critic 修改 `discovery-contract.md` 后 verify-record exit 0 | 完整 artifact hash；reference 变更和 unavailable 必须失败 | 已解决；原 Critic 复验 Closed |
| R12 | 完整 artifact raw-byte hash 受文本 EOL 表示影响 | P1 | GitHub Ubuntu/Windows checkout 均判定本地记录 hash 陈旧；本地 `system-prompt.md` 为 mixed EOL，index 为 LF | UTF-8 文本 LF 规范化、二进制原始字节、artifact v2，并重跑真实 forward | 已解决；working tree/git archive hash 相同 |
| R13 | Windows Actions stdout 为 cp1252，中文输出抛 `UnicodeEncodeError` | P1 | Run `29535953451` 的 self-test/verify-record 在打印中文时失败 | runner 主入口显式 UTF-8，CI `PYTHONUTF8=1` | 已解决；cp1252 独立复现通过 |

## 验证台账

| ID | 关联节点/MUST | 实际验证 | 结果 | 变更标识/时间 | 新鲜度 | 剩余风险 |
|---|---|---|---|---|---|---|
| V1 | N1 | 三个 Agent 分别审查主仓库、13,018 个参考技能和规则/评测冲突 | passed | 本轮 | 新鲜 | 结论尚需实现验证 |
| V2 | N2,N3 | 官方 `quick_validate.py`、引用存在性、YAML 解析、`git diff --check` | passed | 本轮核心与契约改动后 | 新鲜 | Critic 修复后需重跑 |
| V3 | N2 | 真实 Git 基线对照：默认强制上下文代理下降 77.2% | passed | `b3d9a17` vs 当前候选 | 新鲜 | 字符量代理不是精确 tokenizer token |
| V4 | N4 | eval self-test、真实 Git baseline/candidate、坏候选非零、报告哈希一致性 | passed | 最终 runner/rubric/cases | 新鲜 | 离线静态映射不代表模型行为 |
| V5 | N5 | 4 个 TemporaryDirectory 真实安装集成测试；`--force`、七桥接、越界和不完整源 | passed | 最终安装器与测试 | 新鲜 | 云端 Windows/Linux CI 需推送后观察 |
| V6 | N3,N4 | 两个独立新上下文 forward-test；持久记录校验；harness synthetic self-test | passed | 本轮临时仓库与 `forward-tests.json` | 新鲜 | 精确模型/采样配置和原始工具 trace 不可见，已披露 |
| V7 | N2-N7 | 官方技能校验、4 项安装测试、forward self/record/NOT_RUN、eval self/candidate/known-bad、fixture RED、YAML/引用/报告一致性、diff/缓存检查 | passed | 最终候选工作树 | 新鲜 | 云端 CI 只能在推送后观察 |
| V8 | N8 | 远程 SHA、`npx skills --list`、GitHub Actions Ubuntu/Windows | passed | 功能提交 `0cf30f2` | 新鲜 | Actions: `29529506078`，两个矩阵任务均 success |
| V9 | N9,N10 | 三路只读完成审计、参考库 13,018 可发现技能扫描、8 项安装测试、6 项 forward 测试、eval legacy 路由 self-test | passed | 提交 `000ff40` 前后统一复验 | 新鲜 | 等待独立 Critic |
| V10 | N10 | `PYTHONUTF8=1` 官方技能校验、Python 语法、8+6 单测、forward self/record/NOT_RUN、eval self/candidate/known-bad、报告指纹、diff/cache | partially invalidated | 本地提交 `000ff40`，2026-07-17 | Forward record 新鲜度被 F2 推翻；其余证据仍新鲜 | F1/F2 修复后统一重跑 |
| V11 | N11 | F1/F2 Builder 回归、两个 fresh-context Agent、完整 artifact hash、11 项安装测试、10 项 forward 测试、原 Critic 攻击重放 | passed | 修复提交 `bef6b20`，artifact `2213242c…a6e7` | 新鲜 | 远程双 OS CI 待推送 |
| V12 | N11 | 最终本地套件：官方校验、语法、11+10 单测、forward self/record/NOT_RUN、eval self/candidate/known-bad、报告/链接/hash、fixture RED、diff/cache | passed | 最终文档工作树，2026-07-17 | 新鲜 | PowerShell `Out-File` 模块损坏导致一次重定向中断；剩余检查用 Python 子进程复跑通过 |
| V13 | N11 | 推送后 GitHub Actions Ubuntu/Windows | failed | Run `29535953451`，SHA `b3fffeb` | 新鲜 | 两系统 artifact hash 不匹配；Windows 另有 cp1252 输出错误 |
| V14 | N11 | Canonical hash、15 项 forward 测试、新 fresh-context Agent、record、git archive、cp1252 | passed | 提交 `d6476d7`，artifact `02c95241…8458` | 新鲜 | 修复后双 OS CI 待推送 |
| V15 | N11 | 同一 Critic 反向复验 R12/R13 | passed | `/root/final_critic_completion_audit` | 新鲜 | 新增 P0/P1 为 0，Verdict `Approve` |
| V16 | N11 | 再推送前全套：官方校验、11+15 单测、forward self/record/NOT_RUN、eval、archive/cp1252、链接、fixture RED、diff/cache | passed | 状态文档工作树，2026-07-17 | 新鲜 | 验证生成的单个 `__pycache__` 已核对路径并安全清理 |

## 目标追踪

| 目标要求 | 分析证据 | 实现证据 | 验证证据 | 状态 |
|---|---|---|---|---|
| 主项目自动识别 | `docs/project-benchmark-analysis.md` 第 1–2 节 | 仓库结构与入口 | 文件/manifest/CI 扫描 | passed |
| 参考项目扫描与排序 | `docs/reference-scan-report.md` | 候选到 reference/eval 的映射 | 13,018 可发现技能与指定候选深读 | passed |
| 六层差距和迁移分类 | 项目报告第 4–5 节 | 轻量核心、八契约、eval、安装器 | baseline/candidate 与测试 | passed |
| P0/P1/P2 路线图和全栈方案 | 项目报告第 6–7 节 | 当前批和后续 P2 | 原 Critic `Approve` | passed |
| 修改文件、兼容、验证、回滚 | 项目报告第 8 节 | 当前工作树 diff | V12 最终套件 | passed |
| 需要补充的信息 | 项目报告第 9 节 | README 降级方式 | 非阻塞未知项披露 | passed |
| 独立审查和修复复验 | `reviews/final-critic.md` | Builder 修复映射 | 同一 Critic `Approve` | passed |

## 审查循环

| 轮次 | Critic 身份/降级方式 | Verdict | P0/P1 | Builder 修复 | 复验结果 |
|---|---|---|---|---|---|
| 预审 | 三个独立只读 Agent | Request Changes | P0: 默认长协议、不可执行 eval、过度桥接；P1: description、固定流程 | 已完成核心整改 | 进入正式 Critic |
| 1 | `/root/final_critic_2` | Request Changes | P0: 0；P1: F1 静态映射冒充场景、F2 CI 仅 dry-run、F3 状态滞后 | F1-F5 均已修复并取得新鲜证据 | 待原 Critic 复验 |
| 2 | `/root/final_critic_2` | Approve | P0: 0；P1: 0 | F1-F5 全部 Closed | 通过 |
| 3 | `/root/final_critic_completion_audit` | Request Changes | P0: 0；P1: F1 native 安装越界、F2 forward artifact 陈旧 | Builder 修复中 | 待原 Critic 复验 |
| 4 | `/root/final_critic_completion_audit` | Approve | P0: 0；P1: 0 | `bef6b20` 关闭 F1/F2 | 原攻击路径与相邻回归均通过 |
| 5 | GitHub Actions `29535953451` | Request Changes | R12 EOL hash；R13 Windows cp1252 | `d6476d7` 修复 | 待原 Critic 复验 |
| 6 | `/root/final_critic_completion_audit` | Approve | P0: 0；P1: 0 | R12/R13 Closed | working tree/archive、EOL、binary、cp1252 反向复现通过 |

## 外部等待项

无。

## 当前结论

- 当前阶段：再次推送跨平台修复并验证双 OS CI。
- 已完成：项目识别、参考扫描、1–9 报告、安全加固、F1/F2/R12/R13 修复、三轮真实 forward-test 和两轮原 Critic `Approve`。
- 当前主节点：N11。
- 下一步：提交状态文档并再次推送；观察修复后的 Ubuntu/Windows CI，核对远程 SHA、npx 发现和工作树。
- 未验证项：本批改动的双 OS 云端 CI、远程推送和 Claude Code 真实行为仍未执行。
- 剩余边界：格式/安装兼容不等于所有客户端行为一致；历史大提交没有逐规则消融证据，本报告已诚实披露。
