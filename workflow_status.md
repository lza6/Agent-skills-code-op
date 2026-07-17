# Workflow Status

## 当前发布补丁契约（2026-07-17，目标 v1.2.1）

- 目标：让 `main` 中已完成的 provenance 声明核验与 tag-commit 强绑定拥有对应的可复现 Release，而不是只停留在主分支。
- 当前授权：用户已授权按主题 commit/push 和创建 Release；保留 `v1.0.0`、`v1.0.1`、`v1.1.0` 和 `v1.2.0` 作为历史/回滚 tag，绝不移动它们。
- MUST：`v1.2.1` metadata、README、Release 说明、构建器和 tag 一致；ZIP 继续获得 GitHub Artifact Attestation；远端双平台 CI、Release workflow、下载复验和 attestation 验证均成功。
- 当前状态：已完成。`v1.2.1` annotated tag 指向 `45fe743`；双平台门禁 [29592137411](https://github.com/lza6/Agent-skills-code-op/actions/runs/29592137411) 和发布工作流 [29592221435](https://github.com/lza6/Agent-skills-code-op/actions/runs/29592221435) 均成功；下载附件后的 `--expected-commit` 离线复验、`gh attestation verify` 和 tagged `npx.cmd ... --list` 均通过。`v1.2.0` 的线上 Release 已保留且正文已勘误为带 `--targets all --bridges all` 的可执行恢复命令。

## 当前运维加固任务契约（2026-07-17，目标 v1.2.0）

- 目标：关闭多目标安装半完成风险；以机器可读元数据自动构建 Release 制品；通过 tag workflow 创建中文 Release 并为 ZIP 生成 GitHub Artifact Attestation。
- 当前授权：用户明确授权按主题 commit、逐次 push、创建 GitHub Release；不重写 `v1.0.0`、`v1.0.1` 或 `v1.1.0` tag。
- MUST 验收：
  - 安装器失败和异常恢复不会留下半安装，且恢复拒绝被篡改、越界、符号链接或备份缺失的 journal；
  - `release/metadata.json`、构建器、ZIP、checksum、provenance 与 Release 说明一致，构建器可离线复验；
  - 精确三段版本的 annotated tag 触发 Release workflow，ZIP attestation、GitHub Release 附件和中文说明均可从远程复核；
  - 每个主题独立 commit 并在推送前后验证，不把本地 hash 或未执行的 workflow 描述为已签名。
- 当前状态：已完成。三批主题提交 `f3ec20e`（安装事务）、`879f9f3`（制品构建和证明工作流）、`03ad1d9`（中文说明）均已推送；`v1.2.0` annotated tag 指向 `03ad1d9`。
- 远程证据：双平台门禁 [29590997083](https://github.com/lza6/Agent-skills-code-op/actions/runs/29590997083) 成功；发布工作流 [29591153755](https://github.com/lza6/Agent-skills-code-op/actions/runs/29591153755) 成功；[GitHub Release v1.2.0](https://github.com/lza6/Agent-skills-code-op/releases/tag/v1.2.0) 已上传三份附件，下载后构建器复验、`gh attestation verify` 和 tagged `npx.cmd ... --list` 均通过。
- 回滚：安装事务失败自动补偿；发布出现问题时保留已发布 tag，通过新修复版本或安装 `v1.1.0` 回滚，不移动历史 tag。

## 当前发布任务契约（2026-07-17，v1.1.0）

- 目标：将已完成的桥接规则、跨 CLI forward-test matrix、N13 审计文档和验证证据按主题提交并推送到 `main`，创建可核验的 `v1.1.0` tag 与 GitHub Release。
- 复杂度：Deep。
- 当前授权：用户明确授权本地改动审计、分主题 commit、推送、tag、Release、版本化 ZIP、checksum 与 provenance；不运行真实模型 CLI，不部署产品服务。
- MUST 验收标准：
  - commit 以桥接规则、评测实现、审计文档、发布说明拆分，且每批推送后远程 `main` 可见；
  - 本地结构、安装器、eval/forward、known-bad、synthetic forward 与 whitespace 门禁具备新鲜证据；
  - 新 Release 的 tag、目标提交、ZIP、checksum、provenance 和中文说明相互一致；
  - 不把 probe、synthetic 或历史 `v1.0.1` 记录描述成新的真实模型行为样本；
  - 独立代码审查 P0/P1 为零，且未把用户原有无关改动遗漏或混入错误主题。
- 已确认事实：仓库是单技能 Agent Skills 分发、安装与评测项目；`v1.0.1` 是回滚边界，`v1.1.0` 是本轮目标版本。
- 当前用户可见结果：团队可按四个语义清晰的 commit 审查本轮变化，并通过 Release 附件验证版本化技能包。
- 停止条件：tag CI、发布制品和 Release 核验完成；如果 GitHub 权限、远程状态或 CI 失败阻塞，保留已推送提交并如实报告。
- 历史说明：下方原“任务契约”及 N1–N14 是相应时间点的历史证据；本节是当前有效发布状态。

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
- 工作区状态：GitHub Release `v1.0.1` 已发布为 Latest，annotated tag 指向 `9e8eb8c`；本文件是发布后的纯文档记账，不移动既有 tag。
- 关键约束：核心渐进披露；同批 baseline/candidate 评测；只读 Critic；不把未执行检查写成通过。
- 重大假设及反转条件：当前仓库只发布一个技能；若安装器或 `npx skills` 真实行为与 README 不符，必须以运行结果修正文档。

## 节点看板

| ID | 节点目标 | 状态 | 依赖 | 文件/模块 | 验收标准 | 验证方式 | 证据引用 | 回滚 |
|---|---|---|---|---|---|---|---|---|
| N1 | 主仓库、参考技能和规则冲突审查 | passed | - | 全仓库、参考技能根目录 | 给出证据化 P0/P1/P2 与高价值参考 | 三个独立只读 Agent | Agent 审查回传 | 保留 `b3d9a17` |
| N2 | 轻量核心状态机与按需路由 | passed | N1 | `SKILL.md`、`openai.yaml`、长协议入口 | 默认不全文加载长协议；触发边界清晰 | 官方结构验证、字符量、eval | `SKILL.md` 轻量且当前默认上下文代理较基线下降 76.7% | 回退单组规则并复测 |
| N3 | 模块化发现、结果、计划、执行、验证、审查和状态契约 | passed | N1 | `references/` | 每个模块单一职责、中文、无 CLI 强绑定 | diff check、引用完整性、两次 forward-test | 七个模块化 reference（六个契约加一个状态 schema）和一个兼容 reference 均可解析 | 逐模块回退 |
| N4 | 可执行离线评测与视频任务 fixture | passed | N1 | `evals/production-delivery-orchestrator/` | 静态映射不冒充场景执行；真实 Git 基线；真实 forward-test 可追溯 | runner 自测、baseline/candidate、坏候选、forward harness/记录 | 静态状态为 COVERED/UNCOVERED；报告含 SHA-256；真实记录校验通过 | 保留 `cases.yaml` 与 Git 基线 |
| N5 | 跨 CLI 安装器与全面中文 README | passed | N2 | `README.md`、`install_skill.py`、安装测试、CI | 真实临时安装、重复保护、引用完整性和七类桥接通过 | 4 个 stdlib 集成测试；Windows/Linux CI 配置 | 实装、force、越界拒绝、不完整源和文件目标保护均通过 | 备份改名与恢复 |
| N6 | 主线程初步整合与验证 | passed | N2,N3 | 全仓库 | 结构、YAML、安装、eval、远程发现和两次 forward-test有实际证据 | 实际命令和退出码 | 初验完成；Critic 发现评测表述与 CI 覆盖缺口 | 按失败证据最小修复 |
| N7 | 独立 Critic 审查、主线程修复、原 Critic 复验 | passed | N6 | 当前 diff 与验证证据 | 六维审查通过，P0/P1 为零 | 独立只读 Agent | 原 Critic 复验 F1-F5 全部 Closed，Verdict Approve | 仅修复已确认问题 |
| N8 | 提交并推送 GitHub | passed | N7 | Git 历史与远程 | 提交成功、远程 main 可见 | git status/log/remote、远程发现、云端 CI | 功能提交 `0cf30f2` 已推送；Ubuntu/Windows CI 成功；npx 发现新 description | 不改写历史 |
| N9 | 严格 1–9 项目识别与参考对标报告 | passed | N8 | `docs/` | 主项目、参考筛选、差距、迁移、路线图、实施和未知项均有证据 | 文档结构、路径和需求矩阵检查 | `docs/project-benchmark-analysis.md`、`docs/reference-scan-report.md` | 删除本批文档 |
| N10 | 安装器与 forward/eval 证据安全加固 | passed | N9 | installer、forward、eval、tests、CI | symlink 不越界、报告脱敏、记录强校验、legacy 不代打 | 8 项安装测试、6 项 forward 测试、eval 三类 self-test | 主线程统一验证通过；提交 `000ff40` | 回退提交 `000ff40` |
| N11 | 持久化独立 Critic、修复复验和再次发布 | passed | N10 | `reviews/`、README、workflow、GitHub | 六维审查 P0/P1 为零，远程和双 OS CI 成功 | 同一 Critic 复验、Git/Actions/npx | R12/R13 Closed；Actions `29537377916` 双 OS success | 不改写历史 |
| N12 | 增量参考库口径、eval 回归与状态证据收口 | passed | N11 | `docs/`、技能入口、eval/forward、CI、GitHub | 多口径不混用；跨平台指纹稳定；安装器路径可执行；原 Critic 复验；v1.0.1 可复现发布 | 数字/链接、23+11 单测、真实 Forward、`git diff --check`、双 OS CI、Release/tagged npx | A1-A9 Closed；三名原 Critic 最终无 P0/P1 | 回退 N12 主题提交；不移动 `v1.0.1` tag |
| N13 | 当前工作树与参考根新鲜复核、代码库事实文档 | passed | N12 | `docs/codebase/`、既有分析报告、当前仓库、参考根 | 七份事实文档完整；主项目测试重跑；参考根统计独立复算 | scan、11+23 测试、eval/forward、结构计数、子 Agent 回传 | 本地验证、参考审计、主项目审计与文档修正完成 | 删除本轮文档增量，不改产品代码 |
| N14 | 当前分析产物独立六维 Critic 与修复复验 | passed | N13 | `docs/codebase/`、分析报告、workflow | 需求/逻辑/边界/质量/覆盖/运行六维；P0/P1 为零 | 独立只读 Agent；主线程修正文档；原 Critic 复验 | `/root/n13_fast_critic` Verdict `Approve`，术语/快照细化后原 Critic `Reverify: Approve` | 仅回退未通过的分析文档改动 |
| N15 | 用户授权分主题提交与发布 | passed | N14 | 当前工作树、远程 main、Release 目标 | 用户明确要求分主题 commit/push，并创建中文 Release | 当前用户指令、Git/远程状态 | 已授权；`v1.1.0` 发布批开始 | N/A；不重写历史 |
| N16 | 按主题实现跨 CLI matrix 与桥接加固 | passed | N15 | installer、eval/forward、profiles、CI、README | 模糊任务先侦察、失败续修、跨 CLI matrix 与安全执行边界可验证 | 安装器 11/11、eval/forward 35/35、self-test、diff check | 桥接、评测和 CI 已分批提交 | 按独立 commit 回退 |
| N17 | 独立代码 Critic、修复与复验 | passed | N16 | 当前 diff、评测器、profile、报告边界 | P0/P1 为零；宿主环境、目录写入、平台命令、版本匹配和 HOME/TMP 污染均关闭 | 两轮只读 Critic、35/35、diff check | `reviews/v1.1.0-code-review.md`：Approve | 回退未通过批次 |
| N18 | v1.1.0 tag、CI、制品与 GitHub Release | passed | N17 | main、annotated tag、Release assets | tag 指向发布提交；CI、ZIP、checksum、provenance 与中文说明一致 | tag CI、下载核验、`gh release view`、tagged `npx skills --list` | `v1.1.0` → `8666555`；Actions `29586872151` 双 OS success；3 个附件已核验 | 创建后续修复版本；不移动已发布 tag |

## 风险与决策

| ID | 风险或决策 | 等级 | 依据 | 处理方式 | 状态 |
|---|---|---|---|---|---|
| R1 | 默认全文加载 1,560 行长协议 | P0 | 与本地轻量 prompt 规则和渐进披露冲突 | 长协议降为显式/专项兼容层 | 已解决；当前默认上下文代理下降 76.7% |
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
| R14 | 参考根 reparse、结构候选和 `rg` 可发现口径被混写，导致项目边界与排序依据失真 | P1 | 实际有 2,984 个顶层 reparse entries，而旧报告只强调 9 个符号链接并称其余为实体目录 | 重写扫描口径；加入边际增量/主项目覆盖降权和 tie-break；修正 frontmatter 与观察项 | 已解决；文档 Critic 复验 Closed |
| R15 | Eval tree hash 受宿主排序影响，且 Candidate 文件重命名不使指纹失效 | P1 | Windows/POSIX 路径排序不同；拼接文本 hash 不含相对路径 | POSIX 相对名、canonical tree hash、Candidate/Baseline tree 指纹和 rename 回归 | 已解决；Eval Critic `PASS`、23/23 |
| R16 | SKILL 安装器示例依赖错误 cwd；兼容长协议保留固定多 Agent/HTML/覆盖率冲突 | P1 | 从仓库根或用户项目照抄命令失败；显式全文模式会恢复旧刚性规则 | `<skill-dir>` 绝对定位；模块化契约优先级声明 | 已解决；文档 Critic复验 Closed |
| R17 | README 的 `v1.0.1` 稳定安装和附件尚未在 GitHub 物化 | P1 | 审计时远程只有 `v1.0.0`，新工作树无远程 CI | 分主题提交推送、双 OS CI、annotated tag、tag archive、checksum/provenance、远程安装验证 | 已解决；发布/文档 Critic `Approve` |
| R18 | 主分析报告仍有多处把 `v1.0.0` 写成当前发布，并称 tag 为 immutable | P1 | 本地 tag/HEAD 与 `gh release view v1.0.1` 显示当前稳定版为 `v1.0.1`，Release `isImmutable=false` | 区分历史基线、当前稳定版和发布治理边界；修正 N12 时序 | 已解决；等待 N14 复验 |
| R19 | `writing-skills` 排名为高价值候选，但参考证据段缺少对应小节 | P2 | `docs/reference-scan-report.md` 排名表与证据段覆盖不一致 | 补充 frontmatter、Token/引用和 RED/GREEN 清单证据，并声明行号解析规则 | 已解决；等待 N14 复验 |
| R20 | 分析文档把八个 reference 文件误写成“八个模块化契约再加兼容长协议” | P1 | 实际为六个 `*-contract`、一个状态 schema 和一个兼容长协议 | 统一为“七个模块化 reference（六个契约加一个 schema）+ 一个兼容协议” | 已解决；N14 原 Critic 复验通过 |
| R21 | `.codebase-scan.txt` 创建于 N13 事实文档之前，不能作为当前扫描引用 | P1 | 旧快照漏列七份 `docs/codebase/*.md`，文件计数也过时 | 重建当前库存，记录范围、HEAD、排除项与可复跑命令 | 已解决；N14 原 Critic 复验通过 |

## 验证台账

| ID | 关联节点/MUST | 实际验证 | 结果 | 变更标识/时间 | 新鲜度 | 剩余风险 |
|---|---|---|---|---|---|---|
| V1 | N1 | 三个 Agent 分别审查主仓库、13,018 个参考技能和规则/评测冲突 | passed | 本轮 | 新鲜 | 结论尚需实现验证 |
| V2 | N2,N3 | 官方 `quick_validate.py`、引用存在性、YAML 解析、`git diff --check` | passed | 本轮核心与契约改动后 | 新鲜 | Critic 修复后需重跑 |
| V3 | N2 | 真实 Git 基线对照：默认强制上下文代理下降 76.7% | passed | `b3d9a17` vs 当前候选 | 新鲜 | 字符量代理不是精确 tokenizer token |
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
| V17 | N11 | 修复后 GitHub Actions Ubuntu/Windows 完整矩阵 | passed | Run `29537377916`，SHA `da956fb` | 新鲜 | 两个 job 和全部适用步骤均 success |
| V18 | N11 | GitHub 远程技能发现 | passed | `npx.cmd -y skills add https://github.com/lza6/Agent-skills-code-op --list` | 新鲜 | 发现 1 个技能：`production-delivery-orchestrator`；未执行安装 |
| V19 | N12 | 增量审计复核 reparse/入口计数、141/1,560 行数、`nopua` frontmatter、`spec-driven-eval` 和 16,102 并集算法 | passed | 2026-07-17 N12 工作树 | 新鲜 | 文档 Critic 复验 Closed；远程发布另见 R17 |
| V20 | N12 | Eval/Forward `23/23`、Eval self-test、Candidate/Baseline/Known-bad、跨平台固定 tree hash、rename 指纹、报告与 stdout 脱敏 | passed | Latest `b0d725e3…dc30`；Known-bad `955b3980…94c` | 新鲜 | Eval Critic `PASS`；远程双 OS CI 待推送 |
| V21 | N12 | 两个 fresh-context 真实 Forward：模糊修复与 analysis-only；主线程复验 diff、GREEN/RED、clean worktree；严格记录 | passed | artifact `7291cc43…b29d`，fixture `c275ff8` | 新鲜 | 精确模型/采样和完整工具 trace 不可见，已披露 |
| V22 | N12 | 五个主题提交、最终分支/tag CI、annotated `v1.0.1`、Release 三附件、下载 checksum、provenance manifest、tagged npx、v1.0.0 回滚 | passed | release `9e8eb8c`；tag run `29550346228` | 新鲜 | tag 未签名、Release 非 immutable、无 branch protection 为 P2 |
| V23 | N13 | 本轮 Python 语法；安装器 `11/11`；eval/forward `23/23`；eval self-test；candidate `40.0→100.0`、上下文降低 `76.7%`；known-bad `15.8` 且预期 exit `1`；forward synthetic self-test；既有真实记录 verify；`git diff --check`；参考根六种结构口径复算 | passed | HEAD `6b376d85`，2026-07-17；临时报告未入库 | 新鲜 | synthetic self-test 不是模型行为；默认 eval 需要完整 Git 历史和 baseline `b3d9a17`；真实跨客户端矩阵未执行 |
| V24 | N13 | 临时 branch coverage 诊断；本地 tag/远程 Release/资产；最新 HEAD 与 tag CI | passed | 两个 runner 合计 `82%`；`v1.0.1`→`9e8eb8c`；Release 非 draft/prerelease/immutable、3 个资产；Actions `29550854239` 与 `29550346228` success | 新鲜 | coverage 不含子进程安装器且未设门槛；远程检查不是新发布授权 |
| V25 | N14 | 独立六维 Critic、主项目只读审计、修正后原 Critic 复验 | passed | Critic `Approve` → 术语与扫描快照细化 → `Reverify: Approve` | 新鲜 | P2：可将临时覆盖率原始产物与扫描 tree hash 作为后续治理工作；不阻塞分析批准门 |

## 目标追踪

| 目标要求 | 分析证据 | 实现证据 | 验证证据 | 状态 |
|---|---|---|---|---|
| 主项目自动识别 | `docs/project-benchmark-analysis.md` 第 1–2 节 | 仓库结构与入口 | 文件/manifest/CI 扫描 | passed |
| 参考项目扫描与排序 | `docs/reference-scan-report.md` | 候选到 reference/eval 的映射 | 多口径结构审计、可复现并集算法与指定候选深读 | passed |
| 六层差距和迁移分类 | 项目报告第 4–5 节 | 轻量核心、八契约、eval、安装器 | baseline/candidate 与测试 | passed |
| P0/P1/P2 路线图和全栈方案 | 项目报告第 6–7 节 | 当前批和后续 P2 | 原 Critic `Approve` | passed |
| 修改文件、兼容、验证、回滚 | 项目报告第 8 节 | 当前工作树 diff | V12 最终套件 | passed |
| 需要补充的信息 | 项目报告第 9 节 | README 降级方式 | 非阻塞未知项披露 | passed |
| 独立审查和修复复验 | `reviews/final-critic.md` | Builder 修复映射 | Eval、文档、发布三个原 Critic 最终均无 P0/P1 | passed |

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
| 7 | N12 增量只读审计 | Request Changes | P0: 0；P1: A1 参考根口径错误、A2 当前事实/发布时序滞后 | 文档、eval 回归与状态节点分工修复中 | 等待独立 Critic 复验和发布后核对 |
| 8 | `/root/eval_critic` | PASS | P0: 0；P1: 0 | 跨平台 tree hash、结构指纹、CLI 摘要脱敏 | 原问题全部 Closed；23/23 |
| 9 | `/root/docs_critic` | Request Changes — Release Gated | P0: 0；P1: 仅 v1.0.1 尚未物化 | 安装路径、长协议优先级、16,102 算法均已修复 | 原问题 Closed；等待发布后原 Critic 签收 |
| 10 | `/root/docs_critic` | Approve | P0: 0；P1: 0 | 复验 tag、Release、附件、CI、tagged npx 和 v1.0.0 回滚 | A9 Closed |
| 11 | `/root/release_critic` | Approve | P0: 0；P1: 0 | 复验五次 push、tag peel、ZIP manifest、checksum/provenance 和供应链 digest | 原 4 个发布 P1 全部 Closed |

## 外部等待项

无。

## 当前结论

- 当前阶段：v1.1.0 发布批完成；N15–N18 均已通过。
- 历史已完成：N1–N14 和 `v1.0.1` Release 继续绑定各自 tag/commit；本轮不重写其历史结论。
- 当前主节点：N18（`passed`）。
- 下一步：按需在专用环境采集真实客户端行为样本，或进入已披露的 P2 治理工作。
- 当前代码改动：桥接规则、跨 CLI matrix、forward harness、CI、README、N13 审计及发布文档均已按主题提交。
- 未验证项：Claude Code、Cursor、Gemini CLI 等新的真实模型行为样本仍未执行；当前证据为本机 CLI probe、离线/合成测试和历史 v1.0.1 记录。
- 剩余边界：格式/安装兼容不等于所有客户端行为一致；静态 eval 100 分不等于 19 个 prompt 的真实 Agent 执行；选择非隔离宿主执行真实样本仍需要专用测试环境。
