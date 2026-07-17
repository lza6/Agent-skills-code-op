# 参考技能库扫描与候选筛选报告

参考根目录：`C:\Users\Administrator.DESKTOP-EGNE9ND\.claude\skills`

主项目：`production-delivery-orchestrator`

扫描日期：2026-07-17（Asia/Shanghai）

本报告记录参考库的项目边界、去重方法、候选评分和选择依据。它不是把全部技能平均拼接进主项目，而是为跨技术栈迁移提供可复核证据。

## 扫描口径与数量

参考根目录同时包含独立技能、聚合仓库、junction、符号链接、空目录和误放入技能目录的普通代码仓库，因此单一计数会误导。当前增量审计把“文件系统条目”“可作为候选的技能入口”和“工具默认可发现结果”分开统计：

| 口径 | 数量 | 含义 |
|---|---:|---|
| `rg --files -g 'SKILL.md'` | 13,018 | 遵循忽略规则、适合日常可发现候选的保守口径 |
| `rg --files --hidden -g 'SKILL.md'` | 13,058 | 额外包含隐藏目录，但仍遵循部分忽略规则 |
| 顶层条目 | 15,555 | 参考根目录下的全部顶层目录或链接 |
| 顶层 reparse entries | 2,984 | 顶层条目中带 reparse 属性的目录；不是“只有 9 个链接” |
| 同名 `.agents` junction | 2,975 | 名称与目标叶子同名，指向 `.agents\skills` 的同一技能入口 |
| 例外链接 | 9 | 8 个指向 `.cc-switch\skills`，另有异名 `review-skill` 链接；结构候选中排除 |
| 顶层直接 `SKILL.md` | 15,519 | 字面检查顶层条目后直接存在 `SKILL.md`，尚未扣除 9 个例外链接 |
| 合格顶层入口 | 15,510 | 15,519 个直接入口扣除 9 个例外链接；既包含普通目录，也包含去重后的同名 junction |
| 聚合入口 | 129 | 5 个无根级 `SKILL.md` 的聚合目录内，经边界分类得到的有效嵌套技能 |
| 无技能目录 | 31 | 27 个空目录和 4 个普通代码仓库 |
| 结构候选 | 15,639 | 15,510 个合格顶层入口 + 129 个聚合入口 |
| 字面全递归 `SKILL.md` | 16,102 | 不做项目边界折叠的全递归结果，包含顶层技能内部的 demo、模板、备份或子技能 |

这些数字回答的是不同问题，不能互换：`rg` 数量是工具默认可发现性，15,519 是顶层字面入口，15,510 是排除例外链接后的合格顶层入口，15,639 是用于筛选的结构候选，16,102 则是未折叠边界的字面递归全集。字面递归比结构候选多出的 463 个入口主要来自已被视为单一顶层项目的内部 demo、模板、备份或子技能，不直接参与同级排名。

`16,102` 是本机 Windows、Python 3.11 快照的字面路径并集，不是 canonical target 去重数：`Path.rglob("SKILL.md")` 得到 16,093 条路径；再与 15,519 个顶层条目的直接 `entry / "SKILL.md"` 检查结果取字符串路径并集。9 个例外链接只出现在直接检查中，因此并集为 16,102。该遍历不再主动递归已识别的例外链接，不按链接目标去重，也不用于候选排名。可复现核心算法如下：

```python
root = Path(r"C:\Users\Administrator.DESKTOP-EGNE9ND\.claude\skills")
recursive = {str(path) for path in root.rglob("SKILL.md")}
direct = {
    str(entry / "SKILL.md")
    for entry in root.iterdir()
    if (entry / "SKILL.md").is_file()
}
literal_recursive_count = len(recursive | direct)  # 16_102
```

## 项目边界分类规则

1. 顶层条目直接含 `SKILL.md`：先视为入口候选，再解析其 reparse 目标、名称和规范化路径。
2. 顶层无 `SKILL.md`、内部存在多个有效技能：视为聚合仓库，内部技能分别评估。
3. 2,975 个同名 junction 指向 `.agents\skills` 的同名技能，不当成额外实体副本；9 个跨根或异名例外链接从结构候选中排除。
4. 有 README、源码或项目清单但无 `SKILL.md`：视为普通代码仓库、依赖或样例，不作为可安装技能。
5. 空目录或只有生成物：判为无效目录。
6. 声明名称冲突或缺 description：保留为质量风险，不直接作为高价值参考。
7. 测试、demo、模板或 backup：只作为内部材料，不与其父技能重复排名。

## 聚合、普通项目和无效目录

五个聚合目录共提供 129 个结构候选：

- `claude-code-skills`：88 个技能和 demos。
- `hive`：18 个框架预置技能。
- `Raven`：2 个 demo/内部 memory engine 技能。
- `security-test-hskills`：3 个安全技能。
- `skills`：18 个技能及一个脚手架模板。

四个普通代码仓库：`claude-soul`、`DiverseEvol`、`mnemosyne`、`pgjobq`。它们有源码、测试或项目清单，但没有技能入口，不作为独立 Agent Skill 参考。

其余 27 个无技能目录为空目录，包括 `cicd-pipeline-setup`、`code-review-quality`、`database-query-optimization`、`java-unified`、`typescript-unified` 和多个 `ljg-*` 目录。

轻量 frontmatter 检查发现：

- `lazy-senior-dev` 未以 YAML frontmatter 开始；`nopua` 当前以完整 `---` YAML frontmatter 开始，旧扫描结论已纠正。
- 13 个技能没有可识别的非空 description。
- `golang-patterns`、`kotlin-patterns`、`python-patterns`、`web-search-plus` 存在声明名冲突。

这些是文本级风险信号，不等价于完整 Agent Skills Schema 校验。

## 候选评分方法

四个主维度各 1–5 分：

- 业务相似度：是否直接解决技能创建、仓库侦察、调试、计划、验证或多 Agent 编排。
- 架构参考价值：是否提供清晰状态机、职责边界、渐进披露或证据契约。
- 工程成熟度：是否包含脚本、测试、grader、模板、负例和可重复运行资产。
- 可迁移性：能否脱离 Claude/Codex 专属工具，在通用 Agent Skills 中落地。

排序不是四项裸分相加。主项目已经稳定覆盖的能力会降权，候选能补上的未覆盖能力、可复跑证据和边际新增价值会升权。主分相近时依次用“边际增量更高 → 主项目重复覆盖更少 → 工程证据更可复跑 → 专属工具依赖更少”作为 tie-break，避免把成熟但重复的技能排到真正补缺的候选之前。

| 排名 | 候选 | 相似度 | 架构 | 成熟度 | 可迁移 | 边际增量 | 结论 |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | `skill-creator` | 5 | 5 | 5 | 4 | 高 | 最高价值，半迁移 |
| 2 | `testing-skills-with-subagents` | 5 | 5 | 4 | 5 | 高 | 测试方法可直接迁移 |
| 3 | `acquire-codebase-knowledge` | 4 | 5 | 5 | 4 | 高 | 机器扫描思想半迁移 |
| 4 | `systematic-debugging` | 5 | 5 | 4 | 4 | 高 | 科学调试原则可迁移 |
| 5 | `writing-skills` | 5 | 4 | 4 | 4 | 中 | Token 与测试规则选择性迁移 |
| 6 | `subagent-driven-development` | 5 | 5 | 4 | 3 | 中 | Deep 模式半迁移 |
| 7 | `tt-workflow-audit` | 4 | 5 | 4 | 2 | 中 | 仅提炼父协调者架构 |
| 8 | `vc-intent-clarify` | 5 | 4 | 3 | 3 | 中 | 迁移少量澄清决策维度 |
| 9 | `verification-before-completion` | 5 | 4 | 3 | 5 | 低 | 主项目已覆盖，不复制 |
| 10 | `requesting-code-review` | 5 | 4 | 3 | 4 | 低 | 仅吸收 SHA 审查边界 |
| 11 | `dispatching-parallel-agents` | 5 | 3 | 2 | 5 | 低 | 与现有并行规则重复 |
| 12 | `skill-eval` | 5 | 4 | 2 | 4 | 低 | 被 `skill-creator` 上位替代 |
| 13 | `writing-plans` | 4 | 3 | 3 | 3 | 低 | 仅吸收计划自检 |
| 14 | `test-driven-development` | 4 | 3 | 3 | 3 | 低 | 仅吸收红绿证据 |
| 15 | `brainstorming` | 3 | 4 | 4 | 2 | 低 | 不迁移硬批准门 |
| 观察 | `spec-driven-eval` | 4 | 4 | 4 | 4 | 中低 | 观察需求逐项验收和实现/测试分离计分，不进入当前主选 |

## 高价值参考证据

本节中的 `SKILL.md:<line>` 均相对于当前候选标题解析，即 `<参考根>/<候选名>/SKILL.md:<line>`；这样既能定位原始证据，也不把本机绝对用户路径重复写入每一条引用。

### `skill-creator`

- `SKILL.md:86-98`：三级渐进披露，核心正文建议少于 500 行。
- `SKILL.md:169-234`：with-skill 与 baseline 同轮比较、断言和统计。
- `SKILL.md:325-395`：独立盲测、正负触发、训练/留出集。
- 工程资产包含 grader、comparator、analyzer、viewer 和 benchmark 脚本。

迁移：渐进披露、真实 baseline、负向触发、forward-test。拒绝复制 Claude 专属调用和第二套 workspace 格式。

### `testing-skills-with-subagents`

- `SKILL.md:33-42`：RED baseline、GREEN with-skill、REFACTOR 堵漏洞。
- `SKILL.md:46-145`：先观察无技能失败，再用压力场景测试。
- `SKILL.md:166-239`：捕获模型合理化借口并复测。

迁移：脏工作区、用户催促跳过验证、子 Agent 无证据自报成功等压力 case。拒绝“100% compliance”宣传。

### `acquire-codebase-knowledge`

- `SKILL.md:20-30`：结论可追溯，未知与需询问状态分离。
- `SKILL.md:52-99`：机器扫描→意图文档→证据复验。
- `SKILL.md:118-126`：排除生成物，并使用高 churn 文件作为风险信号。

迁移：轻量扫描、intent-vs-reality、统一 unknown/evidence 标记。拒绝每次强制生成七份代码库文档。

### `systematic-debugging`

- `SKILL.md:51-179`：根因调查、单一假设、最小实验、修复前复现。
- `SKILL.md:200-204`：连续失败后升级架构复核。
- `SKILL.md:289`：条件等待优于固定 sleep。

迁移：假设—证据—实验—结论和异步条件等待。拒绝无来源成功率和绝对“三次必定是架构问题”。

### `writing-skills`

- `SKILL.md:99-106`：frontmatter 必填字段、命名与触发描述约束。
- `SKILL.md:217-290`：高频技能的 Token 预算、细节下沉、交叉引用替代重复和精简示例。
- `SKILL.md:600-619`：以 RED/GREEN 清单验证技能，并要求 YAML Schema 与触发条件可检查。

迁移：Token 预算、引用替代复制、frontmatter 约束和技能文档的可验证清单。拒绝把其中的固定字数阈值、专属工具名或绝对流程原样强加给所有客户端。

### `subagent-driven-development`

- `SKILL.md:13-17`：实现、规格审查、代码质量审查分离。
- `SKILL.md:111-123`：结构化完成/担忧/缺上下文/阻塞状态。
- `SKILL.md:241-252`：规格未通过前不进入质量签收。

迁移：Deep 两阶段审查和结构化子 Agent 状态。拒绝给每个微任务固定三个 Agent。

### `tt-workflow-audit`

- `SKILL.md:23-24`：并行 Agent 只读，父协调者串行写共享状态。
- `SKILL.md:83-140`：分区、Schema 输出、父端聚合去重和覆盖披露。
- `workflow-tasktracker-contract.md:43-78`：共享上下文只读、可恢复分区和父端写入。

迁移：父协调者拥有公共文件、并行 Agent 返回结构化 findings。拒绝 TaskTracker/MCP/Claude Workflow 专属实现。

### `vc-intent-clarify`

- `SKILL.md:56-73`：歧义分级路由。
- `SKILL.md:94-146`：轻侦察与深侦察。
- `SKILL.md:195-218`：关键问题和真实路径选项。
- `SKILL.md:569-577`：最多两轮澄清后收敛。

迁移：范围、成功标准、风险面和最多两轮澄清。拒绝固定 RIPER-5、无证据倍数和专属工具。

## 低增量或不建议迁移

- `verification-before-completion`：新鲜证据原则已由主项目更细的 L1/L2/L3 验证契约覆盖。
- `requesting-code-review`：只迁移 BASE/HEAD SHA；主项目已有更完整 P0–P3、证据和置信度格式。
- `dispatching-parallel-agents`：独立任务与自包含提示已经覆盖。
- `skill-eval`：是 `skill-creator` 的简化子集，不引入第二套评测框架。
- `spec-driven-eval`：逐条拆分验收标准、分别评价实现与测试并要求 `file:line` 证据，适合后续对同一 PRD 做可重复比较；但主项目已有 MUST 矩阵、验证契约和 Critic 门禁，且该技能要求显式调用，因此当前只作为 P2 观察项，不引入第二套总分或把二元清单冒充真实行为证明。
- `writing-plans`：吸收规格覆盖自检；拒绝每步粘贴完整代码和固定 2–5 分钟粒度。
- `test-driven-development`：保留红绿证据；拒绝“先写代码就删除重来”的绝对规则。
- `brainstorming`：保留 2–3 个方案与 YAGNI；拒绝所有任务都等待批准、强制提交设计文档。

## 最终选择与主项目映射

| 参考思想 | 主项目落点 |
|---|---|
| 渐进披露、触发边界 | `SKILL.md` 和八个按需 reference |
| 机器侦察与证据契约 | `discovery-contract.md` |
| 老板式结果选择 | `outcome-contract.md` |
| 自适应计划和依赖 | `planning-contract.md` |
| 复现、最小修改、失败续修 | `execution-contract.md` |
| 风险驱动和新鲜证据 | `validation-contract.md` |
| Builder/Critic 分权 | `review-contract.md` |
| 可恢复状态 | `workflow-status-schema.md` 与根 `workflow_status.md` |
| baseline、known-bad、forward-test | `evals/production-delivery-orchestrator/` |

## 置信度与限制

- 顶层条目、2,984 个 reparse entries、15,519/15,510/15,639/16,102 四种结构口径和指定候选证据：高置信度。
- 15,000 级目录未逐文件深读；先用结构/frontmatter 缩减，再深读指定候选。
- 评分是对当前主项目目标的工程判断，不是通用技能排行榜。
- `rg` 的 13,018/13,058 是忽略规则与隐藏目录共同作用下的可发现性快照，不等于结构候选总量。
- 参考库会变化，数量和重复项是 2026-07-17 的快照。
