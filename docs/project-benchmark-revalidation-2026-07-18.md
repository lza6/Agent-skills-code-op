# 当前项目识别、参考对标与改造路线图（2026-07-18）

> **适用快照。** 本报告绑定当前工作树 `eb3bf18ccaa022bf70f6701107c12739871a0200`、本地 `v1.5.0` tag 所解引用的提交 `216dcafa0db925cf08addfd5fbbd31b1b4ad01d8`，以及参考根 `C:\Users\Administrator.DESKTOP-EGNE9ND\.claude\skills` 的本轮扫描结果。它取代旧报告中关于“当前版本为 v1.1.0”的陈述；旧报告仅保留为 2026-07-17 的历史分析快照。本文是实施前/中的问题与路线图；P0/P1 的本地实现和新鲜验证见 [实施闭环报告](implementation-closure-2026-07-18.md)。

> **授权边界。** 本轮只更新分析/状态文档并运行无外部副作用的本地验证。未修改功能代码、依赖、发布物或远端状态；下列代码级路线图必须在用户确认后逐批实施。

## 1. 项目识别结果

### 1.1 主项目识别结论

| 维度 | 结论 | 证据 |
|---|---|---|
| 项目类型 | 单一 Agent Skills 产品的分发、安装、评测与发布工具仓库；不是 Web/API/桌面/移动应用 | `README.md`、`skills/production-delivery-orchestrator/SKILL.md` |
| 语言与框架 | Python 标准库为主，无确认的 Web 框架、ORM、数据库、缓存、消息队列或任务调度器 | `skills/.../scripts/*.py`、`evals/.../*.py`、`release/*.py`；未发现依赖清单 |
| 包/构建 | 没有 `package.json`、`pyproject.toml` 或 lockfile 作为主项目包管理边界；技能安装可用 `npx skills`，发布包由 `release/build_release.py` 生成 | `README.md`、`release/metadata.json`、`release/build_release.py` |
| 运行入口 | Agent 入口：`skills/production-delivery-orchestrator/SKILL.md`；安装器：`scripts/install_skill.py`；仓库盘点：`repository_inventory.py`；离线评测：`run_evals.py`；forward harness：`run_forward_tests.py`；客户端矩阵：`run_client_matrix.py` | 对应文件的 `main()` 与 README 命令 |
| 模块边界 | 核心技能/按需 reference、安装事务、离线 eval 与 fixture、forward/matrix、release/provenance、GitHub Actions、产品/测试/运维文档相互分离 | `skills/`、`evals/`、`release/`、`.github/workflows/`、`docs/` |
| 核心业务流 | 自然语言需求 → `SKILL.md` 路由所需契约 → 本地侦察/实现/验证/独立审查 → 技能安装或离线/forward 评测 → 版本化 ZIP、checksum、provenance、Release | `SKILL.md`、`references/`、`README.md` |
| 配置、日志与错误 | JSON/YAML/Markdown 元数据和 CLI 参数为配置主载体；工具优先输出结构化 JSON/Markdown 并以非零退出报告失败。未发现集中日志、指标或外部告警系统 | `release/metadata.json`、各 runner、`.github/workflows/skill-evals.yml` |
| 测试与部署 | `unittest`、临时目录/真实文件系统/Git fixture、known-bad 反例、双 OS GitHub Actions、tag Release 与 GitHub attestation | `skills/.../tests/`、`evals/.../tests/`、`.github/workflows/` |

置信度：项目类型、语言、入口、模块和测试为高；“不存在数据库/缓存/消息队列”仅限本仓库已扫描的源文件和清单信号，置信度中高，不外推到用户机器或远端服务。

### 1.2 参考项目扫描结果与候选筛选

参考根不是一个单体参考工程：顶层技能及其 `references/`、`scripts/`、`examples/` 中有大量嵌套 `.git`。本轮按**顶层技能项目**去重，先区分“可执行工程”“文档型技能”“声明了脚本但缺失实现的目录”，再按业务相似度、工程成熟度与可迁移性排序。

| 排名 | 候选 | 类型/证据 | 最有价值的可迁移思想 | 适配结论 |
|---|---|---|---|---|
| 1 | `agent-registry` | 可执行 Python registry：`SKILL.md`、`README.md`、`package.json`、`scripts/init_registry.py`、`search_agents.py`、`test_selection.py` 等 | manifest/index、懒加载发现、分页搜索和选择测试 | 高：将来可为多技能发行/能力路由建立独立 schema，而非扫描所有长文档 |
| 2 | `ae-ltd-skill-builder` | 技能生命周期工具：`SKILL.md` 与 `create/validate/lint/fix/test-skill.sh` | 创建→校验→lint→修复→测试的可重复门禁 | 高：迁移门禁分层；实现须改为跨平台 Python，不能复制 Bash 假设 |
| 3 | `workflow-orchestration` | `SKILL.md`、README、templates、教程/how-to/explanation 文档齐全 | 计划→执行→验证→复盘和 lessons 累积 | 高：补强状态可读性与复盘格式；不替换本仓库的风险驱动契约 |
| 4 | `agent-skills-hub-wave` | 文档型安装波次流程 | 批量处理的 inventory、去重、可恢复汇总 | 中高：适合将来多技能目录运营；不适用于单一技能发布主链路 |
| 5 | `benchmark-agents`、`acceptance-orchestrator` | 文档型真实交互评测/验收状态机 | 真实 E2E 证据、DoD evidence、显式升级 | 中：迁移评测门和证据表述，不能迁移其 Claude/终端插件依赖 |
| 6 | `agent-orchestrator`、`agent-evals`、`workflow-runner` | 主要为单 `SKILL.md` 的说明型候选 | 能力匹配、golden dataset、YAML 角色阶段 | 半可迁移：只吸收概念，不将其视为已验证可运行工程 |

`benchmark-e2e` 声明有脚本但本轮目录实际只有 `SKILL.md`，列为无效/宣传性候选；`agent-skills` 供应商绑定，最多借鉴 catalog 分层，不迁移运行模型。

## 2. 主项目现状总结

### 架构特点与已证实优点

- 核心技能保持渐进披露，长协议/专项契约按任务路由；这比固定加载全部规则更适合多 CLI。
- 安装器已实现多目标预检、journal、补偿与项目边界/symlink 防护；25 个安装器/盘点测试在本轮全部通过。
- 评测同时有 baseline、candidate、known-bad 和 fixture，避免把“文字存在”误作通过；当前候选离线 eval 得分 `100.0`，相对 baseline `31.2` 提升 `68.8`。
- forward harness 明确区分 synthetic 自检与真实 Agent 行为，报告和路径具有脱敏/指纹约束；39 个 eval/forward/matrix 测试本轮均通过。
- 发布元数据、版本化 ZIP、checksum、provenance 和 attestation 已形成基本供应链闭环，`release/metadata.json` 当前版本为 `v1.5.0`。

### 当前主要问题、风险与技术债

> **分类口径。** 独立质量审计按当前安全/缺陷严重度得出“无 P0、3 个 P1、5 个 P2”。下表的 `P0（下一次 Release 前）` 是交付路线图优先级：它把会使失败质量门仍可发布的流程缺陷提升为下一次 Release 的硬前置条件，不声称发现了 P0 安全漏洞。

| 等级 | 事实 | 风险 |
|---|---|---|
| P0（下一次 Release 前） | tag Release workflow 未等待质量门；`.github/workflows/release.yml` 直接 build/attest/发布，与 `skill-evals.yml` 并行 | 测试失败的 tag 仍可能创建正式 Release |
| P1 | 真正执行外部 Agent 的 forward harness 使用有界时间但无进程树清理、无 stdout/stderr 总字节上限 | 子进程残留和内存耗尽；`--allow-unsafe-host-execution` 是确认而非隔离 |
| P1（本批关闭） | 旧分析、旧测试说明与历史状态把 v1.1.0/N13 的版本和测试数写成 current | 读者会基于过期事实决策；本报告与状态文件将其明确降格为历史 |
| P1 | 多个 runner 的 `--report-prefix` 未限制为纯文件名 | 本地调用者可经 `../` 逃出指定输出目录 |
| P2 | CI 的 `git diff --check` 在干净 checkout 上通常没有待检 diff | 无法有效拦截 PR/push 的 whitespace 错误 |
| P2 | 未发现自动化 secret/workflow/dependency/SBOM 扫描；无正式覆盖率阈值与跨客户端真实样本门 | 供应链和行为覆盖不足；不应把 39 个静态单测表述成跨 CLI 真实行为证明 |
| P2 | ZIP 验证器整段读取成员而无数量/大小/压缩比上限 | 恶意或异常 release asset 可造成本地资源耗尽 |

## 3. 参考项目亮点提炼

- `agent-registry`：把“寻找合适能力”从目录遍历提升为有版本的索引/manifest 查询。对本项目最有价值的是**可重建索引 + 明确 schema + 选择测试**。
- `ae-ltd-skill-builder`：把作者体验和质量门做成离散命令，减少“写完再想怎么验”的随意性。最有价值的是**validate/lint/test 的独立、可组合门**。
- `workflow-orchestration`：规划、执行、验证、经验沉淀在同一个可回读状态机中。最有价值的是**节点定义、依赖和复盘的可审计表达**。
- `benchmark-agents`/`acceptance-orchestrator`：真实用户旅程的证据不能由静态 prompt 匹配替代。最有价值的是**DoD 与实际运行证据分层**。

共性优点是可发现性、显式阶段边界、可重复验证和对失败的结构化记录。它们不构成把本项目改造成某个 Claude 专用 registry 或固定三 Agent 流水线的理由。

## 4. 差距分析

| 层面 | 当前状态 | 差距/风险 | 参考启发 |
|---|---|---|---|
| 功能 | 单技能分发、安装、离线评测与发布闭环完整 | 没有多技能 catalog/选择层；这是未来规模化需求，非当前缺陷 | `agent-registry` manifest/index |
| 架构 | 按需契约、安装事务和 runner 边界清晰 | Release quality gate 没有依赖化；forward 进程生命周期不够强 | `workflow-orchestration` 的阶段 gate、`benchmark-agents` 的真实运行约束 |
| 工程 | unittest、known-bad、双 OS CI 已存在 | 发布与质量门分离；当前事实文档容易漂移 | `ae-ltd-skill-builder` 可组合 validation 阶段 |
| 性能/资源 | 纯 stdlib、离线 runner 开销低 | 外部 Agent 输出和子进程树无资源界限；ZIP 验证全量读入 | 将资源配额作为 runner API 契约 |
| 安全 | 安装路径/符号链接/journal 控制较强，Actions 已 SHA 固定 | 输出目录前缀、ZIP 解压资源、扫描自动化待补 | 文件名 schema、资源上限、release supply-chain gate |
| 运维 | tag、attestation、provenance 和回滚版本已有 | release 不以测试成功为前置条件；缺少真实客户端样本和兼容矩阵声明 | acceptance evidence 与受控真实 E2E |

## 5. 可迁移 / 半可迁移 / 不建议迁移

| 分类 | 项目/做法 | 原因、收益与适配思路 | 成本与风险 |
|---|---|---|---|
| 可迁移 | `agent-registry` 的 manifest/index/rebuild/search | 使多技能发现可缓存、可测试、可解释；以本仓库 JSON schema 和 Python stdlib 实现，保留现有目录安装兼容 | 中；schema 演进和索引失效策略必须版本化 |
| 可迁移 | `ae-ltd-skill-builder` 的 validate/lint/test 分层 | 让 authoring 与 release gate 共用可调用的质量函数 | 低中；不得强行引入 Bash 或 Claude 专用目录 |
| 可迁移 | `workflow-orchestration` 的阶段/证据/lessons | 让 `workflow_status.md` 只保留一个 current 区块，历史数据显式归档 | 低；避免把 Deep 流程强加给 Quick 任务 |
| 半可迁移 | `benchmark-agents` 真实 E2E | 对关键路线提供强证据，但必须在专用 VM/测试账号、费用上限和最小环境下运行 | 中高；非隔离宿主和付费调用不可默认执行 |
| 半可迁移 | `acceptance-orchestrator` DoD 状态机 | 适合 Release 和高风险改动的完成门 | 中；需要映射到本仓库的 GitHub Actions 和本地 runner |
| 不建议 | 固定 Agent 数/固定长 prompt | 与当前风险驱动、渐进披露设计冲突，会增加成本和上下文污染 | 高；收益不确定 |
| 不建议 | Claude/WezTerm/plugin 专属执行器 | 技术生态不匹配，无法改善 Codex/通用 CLI 的可维护性 | 高；锁定和兼容风险高 |

## 6. 优先级优化路线图

| 优先级 | 做什么、改哪些模块 | 原因/预期收益 | 兼容/数据/回滚 |
|---|---|---|---|
| P0 | 抽取可复用 quality workflow 或在 `release.yml` 内先执行质量门，再允许 build/attest/publish | 阻止失败 tag 形成正式 Release | 不涉及数据迁移；保留手动/历史 tag，回滚为移除 `needs` 或恢复旧 workflow，但不移动已发布 tag |
| P0 | 建立 `docs/current-state.md` 或文档事实一致性检查；将历史快照显式归档 | 防止 current release、测试数和能力陈述漂移 | 无数据迁移；纯文档/CI，回滚为移除新校验 |
| P1 | 加固 forward executor：新进程组/Job Object、超时杀树、流式截断输出、资源界限和回归测试 | 外部 CLI 失败不会残留进程或耗尽内存 | CLI 选项需兼容；新增报告字段以可选字段方式加入；回滚保持旧 runner 行为但不推荐 |
| P1 | 为 `report-prefix` 引入 filename-only validator，并测试 `../`、绝对路径和分隔符 | 恢复 output-dir 边界约束 | 无数据迁移；对不合法历史自动化调用给清晰非零错误 |
| P1 | 验证 ZIP 前限定成员数、单成员/总解压尺寸和压缩比，改为分块 hash | 避免本地验证器 DoS | 无数据迁移；阈值文档化，阈值变化版本化 |
| P2 | 修正 diff gate，新增 secret/workflow lint、低频 SBOM/依赖检查、coverage 基线/阈值 | 改善治理和回归可见度 | 新 CI 环境可能带来 false positive，先 audit-only 后强制 |
| P2 | 在隔离环境建立 Codex/Claude/Gemini 的最小真实样本矩阵 | 把静态 100 分和真实行为证据分开 | 需要明确凭证、配额、环境和隐私边界；不迁移生产数据 |
| P2 | 如出现多技能规模需求，再引入 registry manifest/index | 提升发现性能和可维护性 | 需新 schema/兼容读取器；当前单技能不应提前复杂化 |

## 7. 实施方案

- **前端：** 不适用；仓库没有前端构建或页面。未来若提供 registry UI，应将其作为独立产品，不耦合技能安装器。
- **后端/执行层：** 保持 Python stdlib；优先将 release quality steps 提炼成可重用函数/可调用 workflow，并将 forward 子进程封装为有资源配额的执行器。
- **数据层：** 当前无数据库。P2 registry 使用版本化 JSON manifest 和原子重建/校验和即可，避免为单技能引入数据库。
- **接口层：** 维持既有 CLI flags；新增错误码/JSON 字段应向后兼容。`report-prefix` 失败必须在文件写入前发生。
- **配置：** release metadata 继续作为版本单一来源；为进程/输出/ZIP 限制设置有文档的保守默认值和受控 override。
- **日志与监控：** runner 保持结构化 JSON、输出脱敏和可关联的 artifact hash；真实客户端 runner 记录退出类型、截断标志和清理结果，避免记录凭据或绝对宿主路径。
- **测试：** 继续临时目录与真实子进程 fixture；新增质量 workflow 负向测试、子进程树/输出上限、前缀穿越、ZIP 超限、PR diff base/head。静态单测、synthetic、真实 Agent 样本在报告中分列。
- **部署运维：** release 只能在 quality 成功后发布；先 audit-only 引入供应链扫描，再将稳定规则升格硬门。所有新 Release 只增版本，不重写历史 tag。

## 8. 如果允许改代码：首批文件计划、兼容与回滚

| 文件 | 首批改动目的 | 范围/兼容性 | 验证与回滚 |
|---|---|---|---|
| `.github/workflows/skill-evals.yml`、`.github/workflows/release.yml` | 令发布依赖质量门 | 仅 CI 编排；不改变技能 API | 用故意失败 fixture 证明不创建 Release；回滚 workflow 改动，不移动 tag |
| `evals/production-delivery-orchestrator/run_forward_tests.py`、`evals/production-delivery-orchestrator/tests/test_forward_tests.py` | 进程组、杀树、输出限制 | 保持既有 flags，新增可选限额/结果字段 | 39 项现有测试 + 新负向进程/输出测试；回滚到上个 runner 提交 |
| `run_evals.py`、`run_forward_tests.py`、`run_client_matrix.py` 及对应测试 | 限制 `--report-prefix` | 拒绝此前不安全的前缀；属于安全性破坏性校正 | 路径穿越负例、正常 prefix 回归；按主题提交回滚 |
| `release/build_release.py`、`release/tests/` | ZIP 解压资源限额 | 对异常资产 fail-closed；阈值须文档化 | 新 ZIP bomb/超限成员负例 + 正常 release 验证；按主题提交回滚 |
| `docs/current-state.md`、`docs/codebase/TESTING.md`、`workflow_status.md`、README | 单一当前事实与历史边界 | 文档兼容；不影响安装 | 文档版本/测试数一致性检查与 `git diff --check`；回滚文档主题提交 |

实施节奏：先 P0 的 CI 与事实门，单独验收；再 P1 的 runner/路径/ZIP 加固；最后 P2 治理与真实样本。每批都先写失败测试或可重放负例，保持原有风格，不混入无关重构，不提交/推送/发布，除非用户另行授权。

## 9. 需要补充的信息

下列信息不是本轮分析阻塞项，但决定 P1/P2 的具体实现：

1. 是否授权修改 CI、runner、release builder 和文档，并要求只做 P0，还是 P0+P1？
2. 真实 Agent E2E 的目标客户端、隔离环境、可用测试账号、成本/配额上限和可记录的脱敏证据是什么？
3. 多技能 registry 是近期确定需求，还是仅作为规模化预案？若确定，需要 manifest 的消费者、兼容周期与查询性能目标。
4. Release 应以 workflow 失败即阻断为唯一模式，还是保留具备审计记录的人工 override？推荐默认无 override；若要例外，必须指定角色、理由和可审计路径。

## 本轮执行证据

- `python -m unittest discover -s skills/production-delivery-orchestrator/tests -p "test_*.py" -v`：25/25 通过。
- `python -m unittest discover -s evals/production-delivery-orchestrator/tests -p "test_*.py" -v`：39/39 通过。
- `python -m unittest discover -s release/tests -p "test_*.py" -v`：5/5 通过。
- `python evals/production-delivery-orchestrator/run_evals.py --self-test`：PASS，`llm_calls: 0`。
- `python evals/production-delivery-orchestrator/run_forward_tests.py --self-test`：PASS；明确是 synthetic harness，不是实际 Agent 行为。
- 当前候选 eval：baseline `31.2`，candidate `100.0`，delta `68.8`，默认上下文代理降低 `72.5%`。
- known-bad baseline：candidate `12.3`，预期以 exit `1` 失败；负向门有效。

上述证据不宣称 Claude Code、Cursor、Gemini 或真实付费 Agent 已通过；这些仍是 P2 的受控实测工作。
