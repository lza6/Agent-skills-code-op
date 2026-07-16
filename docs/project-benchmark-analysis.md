# Agent Skills Code OP 项目识别、参考对标与优化实施报告

主项目：`C:\Users\Administrator.DESKTOP-EGNE9ND\Desktop\全能skills\Agent-skills-code-op-repo`

参考根：`C:\Users\Administrator.DESKTOP-EGNE9ND\.claude\skills`

分析日期：2026-07-17（Asia/Shanghai）

本报告严格按用户要求的 1–9 顺序组织。判断以当前仓库、Git 历史、实际测试、远程 CI 和参考技能文件为依据；不适用项明确标为 N/A，不把 fixture 当成真实业务系统。

## 1. 项目识别结果

### 1.1 主项目识别结论

| 识别项 | 结论 | 依据 | 置信度 |
|---|---|---|---|
| 项目类型 | 单技能 Agent Skills 分发、安装与评测仓库；不是 Web 服务、桌面端或传统 SDK | `README.md`、`SKILL.md`、仓库目录 | 高 0.99 |
| 核心产品 | `production-delivery-orchestrator`，将模糊或复杂软件请求推进到可验证交付 | `skills/production-delivery-orchestrator/SKILL.md` | 高 0.99 |
| 主交付语言 | Markdown；技能核心和八个按需契约均为 Markdown | `SKILL.md`、`references/*.md` | 高 0.99 |
| 编程语言 | Python 标准库用于安装、离线 eval 和 forward-test | `install_skill.py`、`run_evals.py`、`run_forward_tests.py` | 高 0.99 |
| TypeScript/TSX | 仅用于故意带缺陷的视频轮询 fixture，不是真实产品前端 | `evals/.../fixtures/video-polling-state-machine` | 高 0.99 |
| Python 框架 | 无；仅使用 `argparse/pathlib/subprocess/json/tempfile/unittest` 等标准库 | Python import 清单 | 高 0.99 |
| 包管理 | N/A；无 pyproject/requirements/npm manifest。`npx skills` 是消费者安装渠道 | 仓库 manifest 搜索、README | 高 0.99 |
| 构建方式 | N/A；无应用构建。CI 执行语法、测试、评测和 whitespace 检查 | `.github/workflows/skill-evals.yml` | 高 0.99 |
| 运行入口 | Agent：`SKILL.md`；安装：`install_skill.py`；评测：`run_evals.py`；真实测试：`run_forward_tests.py` | 文件入口与 `main()` | 高 0.99 |
| 模块划分 | 技能核心、客户端元数据、八个契约、兼容长协议、安装器、测试、eval、fixture、报告、CI | 仓库目录 | 高 0.99 |
| 核心流程 | 原生发现/显式调用/桥接 → 授权分类 → DISCOVER → ALIGN → PLAN → EXECUTE → VALIDATE → REVIEW → CLOSE | `SKILL.md` | 高 0.99 |
| API | 真实业务 API：N/A；fixture 中 fetch 仅为测试样例 | 无服务框架/路由；fixture 文件 | 高 0.99 |
| 数据访问 | N/A；无数据库、Schema、迁移或持久化层 | 全仓依赖与代码搜索 | 高 0.99 |
| 配置管理 | YAML frontmatter、`openai.yaml`、CLI 参数、rubric/cases；无 `.env` 或 Secret | 配置文件与参数解析 | 高 0.98 |
| 日志 | 短命 CLI 使用 stdout/stderr 和 JSON 摘要；无服务型 logger/APM | Python 输出代码 | 高 0.98 |
| 异常处理 | 安装器映射为退出 1；eval 区分 PASS/FAIL/基础设施错误；forward-test 需进一步结构化 timeout | 三个 CLI 的顶层退出逻辑 | 高 0.97 |
| 测试 | 安装集成测试、eval self-test、known-bad、fixture RED、forward harness、Ubuntu/Windows CI | tests、evals、Actions | 高 0.99 |
| 部署 | 生产部署 N/A；交付动作是复制/链接技能到客户端目录 | README 安装章节 | 高 0.99 |
| 数据库/缓存/队列/调度/中间件 | 均 N/A；fixture 的 enqueue 是固定返回，不是真实基础设施 | 依赖与实现搜索 | 高 0.99 |
| 前后端边界 | 真实产品无前后端；`agents/openai.yaml` 是客户端界面元数据，Python 是工具层 | 目录职责 | 高 0.99 |
| 基础设施边界 | GitHub Actions 是唯一 CI 基础设施；无容器、K8s、Terraform | `.github/workflows` 与配置搜索 | 高 0.99 |

当前仓库跟踪 34 个文件。`SKILL.md` 约 142 行、4,471 字符；兼容长协议约 1,561 行、19,879 字符。远程 `main` 在本报告开始时为 `abb0e0d`，工作树干净。

### 1.2 参考项目扫描结果

参考库不是传统“多个完整应用项目”，主体是超大规模顶层技能包集合。可发现口径为 13,018 个 `SKILL.md`；结构扫描还识别出 15,510 个实体根级技能、5 个聚合仓库、9 个有效符号链接、4 个误放的普通代码仓库和 27 个空目录。

去重、分类规则和数量差异详见 [reference-scan-report.md](reference-scan-report.md)。

### 1.3 候选参考项目清单

| 排名 | 候选 | 核心价值 | 可迁移性 |
|---:|---|---|---|
| 1 | `skill-creator` | 渐进披露、baseline、盲测、正负触发 | 高，半迁移 |
| 2 | `testing-skills-with-subagents` | RED/GREEN/REFACTOR、压力场景和合理化测试 | 高 |
| 3 | `acquire-codebase-knowledge` | 机器扫描、证据追踪、intent-vs-reality | 高，半迁移 |
| 4 | `systematic-debugging` | 单一假设、最小实验、条件等待 | 高 |
| 5 | `writing-skills` | Token 预算、引用替代重复、技能测试 | 中高 |
| 6 | `subagent-driven-development` | 实现/规格/质量分权和结构化状态 | Deep 模式半迁移 |
| 7 | `tt-workflow-audit` | 父协调者写共享状态、可恢复分区 | 思想可迁移，工具不可迁移 |
| 8 | `vc-intent-clarify` | 轻/深侦察、范围/成功/风险澄清 | 少量迁移 |
| 9–15 | verification、review、parallel、eval、plans、TDD、brainstorming | 局部原则或负面样例 | 低增量/选择性 |

### 1.4 最终选中的高价值参考及原因

最终采用组合而不是复制单一技能：

1. `skill-creator`：决定轻量核心、按需 references、baseline 与 forward-test。
2. `acquire-codebase-knowledge`：决定模糊请求先扫描、结论必须有证据。
3. `systematic-debugging`：决定先复现、最小实验、失败后重新判断。
4. `testing-skills-with-subagents`：决定对技能自身进行 RED/GREEN 和压力测试。
5. `subagent-driven-development`：决定 Builder/Critic 分权和原 Critic 复验。
6. `tt-workflow-audit`：决定父线程管理共享状态和结构化 Agent 输出。
7. `vc-intent-clarify`：决定只问结果级关键选择并限制澄清轮次。

选择依据是与主项目业务直接相似、能跨 CLI 抽象、已有工程资产、且不会迫使 Quick 任务承担固定重流程。

## 2. 主项目现状总结

### 2.1 当前架构特点

- 142 行轻量入口负责触发、状态机和 reference 路由。
- 八个 90–114 行左右的专项契约按状态加载。
- 1,561 行长协议保留为兼容层，不是默认入口。
- Python 工具全部使用标准库，安装与 eval 不依赖包管理器。
- 离线静态证据、真实 Agent harness、known-bad 和跨平台 CI 分层验证。

### 2.2 当前优点

| 维度 | 评价 | 证据 |
|---|---:|---|
| 功能完整性 | 8.5/10 | 技能、安装、eval、forward、CI 均可运行 |
| 架构清晰度 | 8/10 | 核心/契约/兼容层边界清晰 |
| 模块边界 | 8/10 | skill、references、scripts、tests、evals 分离 |
| 权限模型 | 8.5/10 | 分析、本地修改、高影响外部操作明确分层 |
| 性能 | 8.5/10 | 当前默认上下文字符代理较基线下降 77.2% |
| 测试工程 | 7/10 | 有正向、known-bad、fixture RED、forward 和双 OS CI |
| 安装兼容 | 8/10 | Codex、Claude、`.agents` 和七类桥接 |

### 2.3 当前主要问题

1. 项目识别、参考筛选和迁移决策此前没有形成严格 1–9 的持久报告。
2. 标准桥接路径的符号链接边界弱于 custom bridge，可能写出项目目录。
3. Forward 报告可能原样保存命令、stdout/stderr 中的凭证或敏感数据。
4. `verify_record()` 只能证明字段存在，不能充分验证固定场景和证据完整性。
5. 静态 capability 评分扫描全部 references，可能由默认不加载的长协议提供关键词。
6. `run_evals.py` 约 703 行，多职责；长协议与模块化契约仍有重复维护面。

### 2.4 风险点

- 安装器属于本地文件写入工具，路径与符号链接错误比普通提示词缺陷更危险。
- Forward-test 可能连接真实 Agent CLI，原始输出必须默认脱敏。
- 静态 100 分不能解释为真实模型行为或生产安全 100%。
- Claude Code 与其他 CLI 当前主要证明“格式和安装兼容”，真实行为证据仍以 Codex 为主。

### 2.5 技术债

- 缺正式 Python 最低版本和发布版本元数据。
- 缺 eval 单元测试拆分与覆盖率门槛。
- 多目标安装不是全局事务。
- 历史 `0cf30f2` 是 31 文件的大批提交，无法证明每一组规则都做了独立消融；这是过程证据债务，不能事后伪造。

## 3. 参考项目亮点提炼

### 3.1 按项目亮点

| 项目 | 亮点 | 对主项目价值 |
|---|---|---|
| `skill-creator` | 三级加载、with/without baseline、盲 A/B、触发留出集 | 最高：决定技能架构和评测方向 |
| `testing-skills-with-subagents` | 先复现无技能失败，再用压力 case 堵合理化 | 高：测试技能是否真的改变行为 |
| `acquire-codebase-knowledge` | 机器扫描、证据引用、未知/需询问分离、排除生成物 | 高：支撑模糊请求自动侦察 |
| `systematic-debugging` | 单一假设、最小实验、修复前失败证据、条件等待 | 高：支撑视频/异步任务定位 |
| `writing-skills` | Token 效率、正文引用、过程型技能 TDD | 高：防止规则无限增长 |
| `subagent-driven-development` | 规格审查先于质量审查、结构化 Agent 状态 | 高：增强 Deep 审查闭环 |
| `tt-workflow-audit` | 父线程写共享状态、并行只读、聚合去重、可恢复 | 高：支持长任务编排 |
| `vc-intent-clarify` | 轻/深侦察、关键/有用问题分类、最多两轮 | 中：改善老板式选项 |

### 3.2 共性优点

- 先建立事实和失败证据，再写规则或代码。
- 核心保持短，复杂知识放 reference 或脚本。
- 独立 Reviewer 不相信 Builder 自报成功。
- 验证要运行，并记录退出码、diff 和未验证项。
- 并行仅用于真正独立任务，共享状态由父线程收口。
- 流程必须能停止，不能为 P2/P3 无限扩张。

### 3.3 对主项目最有价值的亮点

最有价值的是“渐进披露 + 证据优先侦察 + 独立审查 + 技能自身 eval”。这些已经映射到 `SKILL.md`、discovery/execution/validation/review 契约和 eval 目录。专有工具、固定 Agent 数和硬批准门没有迁移。

## 4. 差距分析

| 层级 | 基线短板 | 当前改善 | 剩余差距 |
|---|---|---|---|
| 功能层 | 模糊请求可能先问用户；测试失败易交回用户 | 自动侦察、失败续修、异步任务专项、结果选项 | 真实 Claude/其他 CLI 行为样本不足 |
| 架构层 | 每次强制加载长协议；description 承载工作流 | 轻量状态机和八个按需契约 | 长协议与模块契约仍重复；eval 单文件偏大 |
| 工程层 | 无可执行 eval、无真实安装测试、无 CI | baseline、known-bad、forward harness、4 项安装测试、双 OS CI | 缺正式版本元数据、覆盖率和更多单元测试 |
| 性能层 | 默认加载约 20K 字符长协议 | 当前默认上下文代理下降 77.2% | Deep 多 reference 累积成本仍需真实 token/延迟采样 |
| 安全层 | 桥接过度触发；路径/输出边界未系统测试 | 权限分层、custom path 防逃逸、force 保护 | 标准桥接 symlink、forward 脱敏和记录可信度需本批修复 |
| 运维层 | 安装说明和远程验证不足 | README、npx、Python 安装器、Actions | 多目标事务、版本发布和制品校验仍是 P2 |

## 5. 可迁移 / 半可迁移 / 不建议迁移

| 分类 | 内容 | 原因 | 收益 | 成本 | 风险 | 适配思路 |
|---|---|---|---|---|---|---|
| 可迁移 | 渐进披露 | 与 Agent Skills 原生加载一致 | 降低冲突和上下文成本 | 低 | 路由漏读 | 核心列明每个 reference 的读取条件 |
| 可迁移 | 新鲜证据完成门 | 跨技术栈通用 | 减少虚假完成 | 中 | 低风险任务过测 | L1/L2/L3 风险分层 |
| 可迁移 | 单一假设和最小实验 | 调试领域通用 | 更快定位根因 | 低 | 可能过早收敛 | 保留反证和候选集合 |
| 可迁移 | 父线程写共享状态 | 避免并发覆盖 | 稳定多 Agent 合并 | 中 | 父线程瓶颈 | 只并行只读或不重叠文件任务 |
| 半可迁移 | 机器代码库扫描器 | 有价值但项目栈多样 | 降低用户定位成本 | 中高 | 扫描器变成硬依赖 | 先契约化，脚本作为可选能力 |
| 半可迁移 | 两阶段规格/质量审查 | Deep 有价值 | 减少需求遗漏 | 中 | Quick 成本过高 | 仅 Deep/高风险 Standard 启用 |
| 半可迁移 | 严格 TDD | 核心逻辑有效 | 回归证据强 | 中 | 遗留/文档任务不适用 | 允许等价复现证据 |
| 半可迁移 | 歧义打分 | 能帮助路由 | 减少无效问题 | 中 | 分数伪精确 | 使用定性风险维度而非固定公式 |
| 不建议 | 每任务固定三个 Agent | 与风险驱动冲突 | 无 | 高 | 成本、延迟、上下文污染 | 由依赖和风险决定 Agent 数量 |
| 不建议 | 所有任务等待批准 | 与用户要求的自治冲突 | 极低 | 高 | 阻塞小白用户 | 仅产品取舍和外部高影响操作询问 |
| 不建议 | Claude/TaskTracker/MCP 专属实现 | 无法跨 CLI | 局部 | 高 | 工具锁定 | 只抽象为能力契约 |
| 不建议 | 固定全量验证/HTML/测验 | 与项目风险无关 | 低 | 高 | 污染仓库和浪费时间 | 按资产和风险选择门禁 |

## 6. 优先级优化路线图

| 优先级 | 做什么 | 为什么 | 模块 | 预期收益 | 风险 | 数据迁移 | 兼容性 |
|---|---|---|---|---|---|---|---|
| P0 已完成 | 取消默认全文长协议 | 核心上下文冲突 | SKILL、桥接、README | 当前默认字符代理下降 77.2% | 路由漏读 | N/A | 向后兼容，长协议仍保留 |
| P0 已完成 | 建立可执行 eval 和 known-bad | 防止规则删坏 | evals、CI | 同批 baseline/candidate 可复测 | 静态分数被误解 | N/A | 无运行 API 变化 |
| P0 已完成 | 模糊请求先扫描 | 小白无法定位代码 | discovery、SKILL | 减少无价值提问 | 扫描越界 | N/A | 保留专家约束 |
| P1 本批 | 标准桥接 symlink 防逃逸 | 防止项目外写入 | installer/tests | 收紧文件边界 | 拒绝少数依赖 symlink 的非常规仓库 | N/A | 正常目录不受影响 |
| P1 本批 | Forward 报告脱敏和强校验 | 防 Secret 入库和伪记录 | forward runner/tests | 提升审计可信度 | 过度脱敏影响调试 | N/A | CLI 参数不变 |
| P1 本批 | Eval 使用运行时可达 references | 防长协议关键词代打 | eval runner/reports | 100 分更接近真实路由 | 评分可能下降 | N/A | 报告 Schema 扩展 |
| P1 本批 | 持久化 1–9 分析与 Critic | 满足目标输出和恢复 | docs/reviews/workflow | 证据可追溯 | 文档维护成本 | N/A | 无行为变化 |
| P2 | 拆分 703 行 eval runner | 降低多职责维护风险 | evals | 更易单测 | 重构回归 | N/A | 保持 CLI |
| P2 | 多目标安装事务 | 防中途失败残留 | installer | 更强原子性 | 实现复杂 | N/A | 需保持 force 行为 |
| P2 | Claude/更多 CLI 真实矩阵 | 区分格式兼容和行为兼容 | forward reports | 更强泛化证据 | 需要环境和凭证 | N/A | 不改变技能接口 |
| P2 | 版本和发布元数据 | 长期维护 | 根目录、release | 可重复发布 | 流程成本 | N/A | 新增不破坏 |

## 7. 实施方案

### 7.1 前端改造建议

真实产品前端 N/A。`agents/openai.yaml` 是客户端展示接口，应继续保持 display name、short description 和 default prompt 与 SKILL 同步。TSX 只作为 fixture，不应引入 React 构建系统。

### 7.2 后端改造建议

真实服务后端 N/A。Python CLI 是工具层：优先标准库、稳定退出码、结构化错误和无副作用 dry-run。本批强化路径安全、timeout 和脱敏。

### 7.3 数据层改造建议

数据库、缓存、队列和迁移 N/A。评测 JSON 是文件产物，应增加 Schema 校验、内容哈希和敏感信息过滤；不要引入数据库只为保存报告。

### 7.4 接口层改造建议

保持现有 CLI 参数和 Agent Skills 目录结构。对不安全路径返回明确非零退出；forward 报告扩展字段时保持旧读者仍可忽略新增字段。

### 7.5 配置管理建议

继续使用 `openai.yaml`、rubric、cases 和 CLI 参数。P2 可声明 Python 最低版本，但不为零依赖项目引入重型配置框架。

### 7.6 日志与监控建议

短命 CLI 不需要 APM。stdout 给用户结果，stderr 给错误，JSON 报告用于审计。敏感命令和输出必须脱敏；未来可增加 `--verbose`，默认保持简洁。

### 7.7 测试策略建议

- 安装器：真实 TemporaryDirectory、symlink、dry-run、标记损坏和失败回滚。
- Eval：当前/历史 baseline、known-bad、legacy exclusion、负向触发。
- Forward：synthetic harness 自测与真实 Agent 记录严格分开。
- 技能行为：压力场景覆盖跳过发现、覆盖脏改动、无证据完成和外部越权。
- CI：Ubuntu/Windows 同批运行，未执行项不得写成通过。

### 7.8 部署与运维建议

生产部署 N/A。交付是 GitHub 发布和技能安装：远程 SHA、Actions、`npx skills --list` 和 Python 安装测试构成发布证据。P2 再考虑版本 tag 和 release automation。

## 8. 如果允许改代码：文件计划与实施约束

用户已在目标结尾要求“制定计划并完成开发”，因此当前批次已获得本地修改、测试和推送授权。修改前公开计划如下：

| 文件 | 目的 | 范围 | 兼容性 | 验证 | 回滚 |
|---|---|---|---|---|---|---|
| `docs/project-benchmark-analysis.md` | 固化 1–9 输出 | 新文档 | 无行为影响 | 标题/链接/需求矩阵检查 | 删除文档 |
| `docs/reference-scan-report.md` | 固化扫描和候选证据 | 新文档 | 无行为影响 | 路径、数量、候选一致性 | 删除文档 |
| `reviews/final-critic.md` | 固化六维审查和复验 | 新文档 | 无行为影响 | Critic 对照 | 删除文档 |
| `install_skill.py` | 标准桥接边界和标记校验 | 路径预检 | 正常目录兼容；拒绝不安全 symlink | 安装 unittest | 回退本批脚本改动 |
| `test_install_skill.py` | 增加安全回归 | 新测试分支 | 无运行影响 | unittest | 回退测试 |
| `run_forward_tests.py` | 脱敏、强记录校验、timeout 结构化 | 报告层 | CLI 参数保持 | 新单元测试/self-test | 回退 runner |
| `tests/test_forward_tests.py` | 防伪记录和脱敏回归 | 新测试 | 无运行影响 | unittest | 删除测试 |
| `run_evals.py`、报告 | 排除默认不可达 legacy 代打 | 评分语义 | 报告新增证据字段 | self/candidate/known-bad | 回退评分批次 |
| CI、README、workflow | 接入测试和证据入口 | 文档/流水线 | 安装命令不变 | YAML、Actions、远程核对 | 回退该批 |

当前批次不修改技能名、用户数据或公共 API，不做无关重构，不进行生产/付费操作。历史大批提交无法事后伪造成小步消融；本轮按“文档证据→安全修复→Critic/状态”分批提交。

## 9. 需要补充的信息

### 阻塞完成的信息

当前无必须由用户补充的阻塞信息。

### 可选信息

- 若要证明 Claude Code 的真实行为兼容，需要用户指定可用版本、模型和是否允许启动真实 CLI forward-test。
- 若要建立正式发布版本，需要用户决定 SemVer、tag 和 release note 策略。
- 若要使用真实付费 Agent/API 做大规模 eval，需要明确费用上限和凭证边界。

在这些信息缺失时，当前结论严格限定为：Agent Skills 格式、目录安装和项目桥接兼容已验证；真实模型行为证据以 Codex 新上下文 fixture 为主，不外推为所有客户端 100% 一致。
