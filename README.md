# Agent Skills Code OP：生产级软件交付编排技能

`production-delivery-orchestrator` 是面向 Codex、Claude Code 和兼容 Agent Skills 工具的软件交付技能。它将模糊或复杂的软件需求转换为有边界、可执行、可验证、能停止的交付工作流。

它的核心理念是：

> 用户决定最后要看到什么结果；智能体根据真实仓库完成技术侦察、实现、测试和验收，同时在生产、外部写入、付费和破坏性操作前停下来确认。

## 项目分析与审计证据

- [项目识别、差距、迁移与 1–9 实施报告](docs/project-benchmark-analysis.md)
- [参考技能库扫描、去重与候选评分](docs/reference-scan-report.md)
- [独立 Critic 六维审查与复验](reviews/final-critic.md)
- [持久工作流状态](workflow_status.md)

参考根目录规模很大：日常 `rg` 可发现口径为 13,018 个 `SKILL.md`，结构扫描还包含隐藏、符号链接和聚合目录。仓库没有平均拼接全部规则，而是按业务相似度、架构价值、工程成熟度和可迁移性筛选高价值候选。

## 适合什么任务

- “帮我修复视频任务问题”一类只有现象、没有文件位置的模糊请求；
- 跨前端、后端、API、数据库、异步任务或 AI Agent 的端到端实现；
- Bug 修复、重构、测试补齐、代码审查、上线前检查；
- 需要根据失败结果继续修复和复验的复杂任务；
- 需要 Builder、Critic 或 Evaluator 独立验收的高风险任务。

以下情况通常不需要启用完整交付编排：

- 非软件请求；
- 简单事实问答；
- 只需要解释一个概念或生成一个孤立代码片段；
- 单行、低风险且已有明确验证方式的机械修改。

## 工作方式

```text
用户请求
  ↓
判断是否需要生产交付编排
  ↓
读取 SKILL.md
  ↓
按任务类型和风险读取必要的 reference
  ├─ 模糊故障：先侦察仓库和用户旅程
  ├─ 结果有歧义：提供结果化选项
  ├─ 只分析：只读诊断，不修改代码
  └─ 明确修复：本地实现、测试、失败后续修
  ↓
达到验收标准，或遇到真实权限/环境阻塞后停止
```

技能采用渐进披露。安装器生成的项目桥接只负责判断何时读取 `SKILL.md`，不会要求每个软件请求都全文加载 `references/system-prompt.md` 或全部参考文档。

## 三类接入方式必须区分

不同 CLI 对 Agent Skills 的支持并不完全相同。不存在一个目录能保证所有工具都原生自动发现和自动调用。

| 接入方式 | 作用 | 适合场景 | 注意事项 |
|---|---|---|---|
| 原生技能发现 | 工具扫描技能目录，根据 `name` 和 `description` 选择技能 | Codex、Claude Code 或其他原生支持 Agent Skills 的客户端 | 是否隐式调用取决于客户端版本和配置 |
| 显式调用 | 用户直接指定技能名 | 需要确定使用本技能，或自动匹配不稳定时 | 最可靠、最容易排错 |
| 项目规则桥接 | 在 `AGENTS.md`、`CLAUDE.md` 等规则文件中写入轻量路由说明 | 工具不支持原生发现，或团队希望项目内统一路由 | 桥接始终可见，但不会强制全文加载长协议 |
| 普通文件引用 | 告诉智能体读取技能路径 | 不支持上述机制的 CLI 或 IDE | 需要在任务中显式说明路径 |

## 推荐安装：`npx skills`

本仓库遵循通用 [Agent Skills 规范](https://agentskills.io)。推荐使用 [`skills`](https://github.com/vercel-labs/skills) CLI 安装。

以下命令默认锁定稳定版 `v1.4.1`。完整的 GitHub `tree/v1.4.1` 地址是版本边界，避免安装结果随 `main` 后续提交变化。

### 交互式安装

```bash
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1
```

Windows PowerShell 如果拦截 `npx.ps1`，直接使用：

```powershell
npx.cmd skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1
```

### 全局安装到 Codex 和 Claude Code

```bash
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1 \
  --skill production-delivery-orchestrator \
  --global \
  --agent codex claude-code
```

PowerShell 单行形式：

```powershell
npx.cmd skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1 --skill production-delivery-orchestrator --global --agent codex claude-code
```

### 安装到当前项目

在目标项目根目录执行：

```bash
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1 \
  --skill production-delivery-orchestrator \
  --agent codex claude-code
```

项目级安装便于团队共享，但实际安装目录和链接方式由 `skills` CLI 及目标工具决定。

### 查看仓库中的技能

```bash
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1 --list
```

### 不安装，生成一次性使用提示

```bash
npx skills use https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1 --skill production-delivery-orchestrator
```

### 版本切换、升级和回滚

`skills update` 更新的是已安装记录，不适合表达“明确切换到哪个仓库版本”。需要升级或回滚时，先移除旧副本，再用目标 tag 的完整地址重新安装。

锁定或恢复到 `v1.4.1`：

```bash
npx skills remove production-delivery-orchestrator --global --yes
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.1 \
  --skill production-delivery-orchestrator \
  --global \
  --agent codex claude-code \
  --yes
```

回滚到 `v1.4.0`：

```bash
npx skills remove production-delivery-orchestrator --global --yes
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/v1.4.0 \
  --skill production-delivery-orchestrator \
  --global \
  --agent codex claude-code \
  --yes
```

项目级安装执行相同步骤，但去掉 `--global`。切换后建议新开任务或重启对应 CLI，使其重新扫描技能。

### 开发版 / 滚动版本

只有需要验证尚未发布的改动时才使用 `main`。它会随新提交变化，不是可复现的稳定安装来源。

```bash
npx skills add https://github.com/lza6/Agent-skills-code-op/tree/main \
  --skill production-delivery-orchestrator \
  --global \
  --agent codex claude-code
```

这些命令已用 `skills` CLI `1.5.13` 的 `--help` 接口核对；带 tag 的 `tree/<version>` 地址也已通过远程只读发现验证。仓库版本已由 tag 锁定，但普通 `npx skills` 仍会取得当时最新的 CLI；需要连安装工具版本也固定时，可把命令前缀改为 `npx -y skills@1.5.13`。后续版本如果改变参数，以目标版本的 `npx skills --help` 为准。

## Release 制品、校验和与来源核对

[`v1.4.1` Release](https://github.com/lza6/Agent-skills-code-op/releases/tag/v1.4.1) 提供以下项目发布附件：

- `production-delivery-orchestrator-v1.4.1.zip`：版本化技能包；
- `SHA256SUMS.txt`：记录上述 ZIP 与 `provenance.json` 的 SHA-256；
- `provenance.json`：记录 tag、commit、canonical artifact hash、逐文件 manifest、元数据哈希和 attestation 策略。

下载三个附件后，在 Linux/macOS 上核对：

```bash
sha256sum --check SHA256SUMS.txt
```

Windows PowerShell 可分别计算后，与 `SHA256SUMS.txt` 中同名文件的值逐字比较：

```powershell
Get-FileHash .\production-delivery-orchestrator-v1.4.1.zip -Algorithm SHA256
Get-FileHash .\provenance.json -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

再检查 `provenance.json` 的 `tag` 为 `v1.4.1`，其 `commit` 与 annotated tag 解引用后的提交一致：

```bash
git ls-remote https://github.com/lza6/Agent-skills-code-op.git \
  refs/tags/v1.4.1 'refs/tags/v1.4.1^{}'
```

`release/metadata.json` 是版本、tag、兼容范围、Release 说明和证明策略的单一来源；`release/build_release.py` 可从同一份元数据复建并验证三份附件。`npx skills` 不会自动读取这些附件，GitHub 自动生成的 “Source code (zip)” 与 “Source code (tar.gz)” 也不等于项目发布附件。

本地 SHA-256 只证明完整性。`v1.4.1` 的 ZIP 必须在 GitHub `release` workflow 的 Artifact Attestations 步骤成功后，才具有可验证的构建证明：

```bash
gh attestation verify production-delivery-orchestrator-v1.4.1.zip \
  --repo lza6/Agent-skills-code-op
```

不要把没有该验证结果的附件描述为“已签名”；历史 `v1.1.0` 的三份附件仍仅提供 checksum/provenance。

## Codex 的使用方式

### 原生发现

用户级技能通常安装到：

```text
~/.codex/skills/production-delivery-orchestrator/
```

项目级 Python 安装器会写入：

```text
.codex/skills/production-delivery-orchestrator/
```

安装后建议新开一个任务，让 Codex 重新扫描技能。

### 显式调用

```text
使用 $production-delivery-orchestrator 修复视频任务无限轮询问题，并完成相关验证。
```

如果当前 Codex 客户端未自动匹配技能，显式调用是首选降级方式。

## Claude Code 的使用方式

用户级技能通常安装到：

```text
~/.claude/skills/production-delivery-orchestrator/
```

项目级 Python 安装器会写入：

```text
.claude/skills/production-delivery-orchestrator/
```

显式使用示例：

```text
请使用 production-delivery-orchestrator，先扫描当前仓库，再修复视频任务问题。
```

Claude Code 是否根据 description 自动选择技能取决于具体版本、会话和配置。如果没有自动触发，可显式指定技能，或生成 `CLAUDE.md` 项目桥接。

## 通用 CLI 和其他编码智能体

支持通用 Agent Skills 的工具可以使用：

```text
~/.agents/skills/production-delivery-orchestrator/
.agents/skills/production-delivery-orchestrator/
```

对于不支持原生技能发现的工具，使用项目规则桥接。自带安装器支持：

- `AGENTS.md`；
- `CLAUDE.md`；
- `GEMINI.md`；
- `.github/copilot-instructions.md`；
- Cursor Rules；
- Windsurf Rules；
- Cline Rules；
- 任意项目内自定义规则文件。

桥接文件只写入带开始和结束标记的受管区块，不会覆盖文件中的其他内容。

## 自带 Python 安装器

Python 安装器适合离线环境、明确目录安装和项目规则桥接。它不依赖 Node.js。

先克隆仓库：

```bash
git clone --branch v1.4.1 --depth 1 https://github.com/lza6/Agent-skills-code-op.git
cd Agent-skills-code-op
```

### 安装前演练

```bash
python skills/production-delivery-orchestrator/scripts/install_skill.py \
  --scope project \
  --project-dir /path/to/project \
  --targets all \
  --bridges all \
  --dry-run
```

`--dry-run` 只打印计划，不写入文件。

### 用户级安装

```bash
python skills/production-delivery-orchestrator/scripts/install_skill.py \
  --scope user \
  --targets all
```

用户级目标包括 Codex、Claude Code 和通用 `.agents/skills` 目录。

### 项目级安装并生成桥接

```bash
python skills/production-delivery-orchestrator/scripts/install_skill.py \
  --scope project \
  --project-dir /path/to/project \
  --targets all \
  --bridges all
```

### 自定义桥接路径

```bash
python skills/production-delivery-orchestrator/scripts/install_skill.py \
  --scope project \
  --project-dir /path/to/project \
  --targets agents \
  --custom-bridge .other-agent/rules.md
```

自定义桥接必须是项目内相对路径，安装器会拒绝越出项目根目录的路径。

### 重复安装与替换

- 同一目标已存在时，安装器默认停止，避免静默覆盖；
- 确认要替换安装副本时才使用 `--force`；
- 桥接区块可重复运行，安装器会原位更新受管区块，不会重复追加；
- 推荐先执行 `--dry-run`，再执行真实安装。

### 跨目标失败恢复

一次安装中的所有原生目标和桥接文件是一个可补偿事务：全部预检和快照后才写入；中途失败会逆序恢复已修改的目录及桥接原文。异常中断时会留下 journal，并阻止新的安装覆盖它。请使用**原安装相同的** scope、targets、bridges、custom bridge 和项目目录恢复，例如：

```bash
python skills/production-delivery-orchestrator/scripts/install_skill.py \
  --scope project \
  --project-dir /path/to/project \
  --targets all \
  --bridges all \
  --recover
```

恢复会拒绝路径越界、符号链接、篡改的 journal 和缺失备份；遇到这类报错不要删除 journal 后重试，应先保留现场并核对目标项目。

## 手动安装

必须复制整个技能目录，不能只复制 `SKILL.md`。技能会按任务需要读取 `references/`，安装器也位于 `scripts/`。

```text
production-delivery-orchestrator/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
└── scripts/
    └── install_skill.py
```

手动安装时，将整个目录复制到目标工具实际支持的技能目录。不要假定某个第三方工具一定识别 `.agents/skills`；应先查该工具版本的官方说明。

## 安装后如何提出任务

### 小白用户的模糊请求

```text
帮我修复视频任务问题。
```

当当前目录是唯一相关仓库时，技能应先扫描项目规则、相关代码、状态流、测试和用户旅程，不要求用户先指出文件、函数、测试框架或根因。

### 资深开发者的完整请求

```text
修复 packages/web/src/hooks/useVideoJob.ts 中 failed 状态仍继续轮询的问题。
保持 API Schema 兼容，不增加依赖，补充 Vitest 回归测试，并运行 web 包的 typecheck、test 和 build。
```

技能应保留这些技术约束并直接执行，不用新手选项重新询问已经明确的交付层级。

### 只分析，不修改

```text
审查视频任务为什么会无限轮询，先不要修改代码。
```

技能可以扫描和运行非破坏性诊断，但不得自动修改代码。

### 明确授权修复

```text
修复视频任务重复提交和重复扣额度问题，并根据测试失败继续修复，直到验收通过或遇到真实外部阻塞。
```

“修复、实现、完成、落地”授权范围内的本地编辑和非破坏性验证，不代表授权部署、推送、真实付费调用或生产写入。

## 关于长规则和 `system-prompt.md`

`references/system-prompt.md` 保留了完整交付协议和跨工具适配背景，但不应因为文件只有几十 KB 就在每个任务中强制全文加载。

原因很直接：

- 上下文窗口还要容纳用户请求、仓库代码、项目规则、测试和工具结果；
- 重复规则和无关门禁会增加冲突；
- Quick 任务不需要 Deep 任务的多 Agent、HTML 报告或迁移流程；
- 强模型更适合读取清晰的目标、成功标准、权限边界和当前任务所需模块。

因此，默认行为是：先读取 `SKILL.md`，再按任务路由加载必要参考。只有用户明确要求完整协议审计，或技能当前路由确实需要完整背景时，才读取长协议的相关内容或全文。

不建议直接用原始 `GPT5.6全栈规则提示词（codex版）.txt` 覆盖跨工具版本。原始文本中的 Codex 专属假设、本机绝对路径和单一规则入口不适合 Claude Code 与其他 CLI。若要保留原版，应作为历史参考另存，而不是替换默认运行规则。

## 自适应侦察、审查和测试证据

技能只在需要时加载 `references/adaptive-delivery-contract.md`。它提供一项可选的文件名盘点工具，不读取源码或执行项目，且不会因为 Python 缺失、输出截断或项目不适配而阻塞人工侦察：

```bash
python skills/production-delivery-orchestrator/scripts/repository_inventory.py \
  --root /path/to/repository
```

输出仅含相对路径、语言/构建信号和入口/测试候选，仍须读取真实代码与调用链。Deep 与高风险 Standard 采用“实现前规格审查 + 实现后质量审查”；Quick 与普通 Standard 不生成空 Spec。核心逻辑优先测试先行；遗留、集成和文档任务可采用可追溯的等价复现证据。歧义依据可见结果、兼容/数据、外部影响和范围/证据进行定性判断，而非固定打分公式。

## 安全边界

技能不会因为“自动完成”而自动执行以下动作：

- 生产部署或生产配置修改；
- 远程推送、合并或发布；
- 真实外部系统写入；
- 会产生费用的真实 AI、图片或视频 API 调用；
- 删除、覆盖或批量修改重要数据；
- 不可逆操作或实质性扩大任务范围。

这些动作仍需明确授权。安全的本地读取、范围内修改、测试、类型检查、Lint、构建和 Mock 验证可根据用户的修复或实现请求直接进行。

安装器会拒绝越出项目目录的项目级原生安装目标、标准桥接和自定义桥接，包括经文件或父目录符号链接解析到项目外的路径。Forward-test 报告会在落盘前脱敏 Authorization、Bearer、常见 API Key/Token 和 secret 参数；不要把真实凭证直接写进命令模板。

## 技能自身验证

仓库包含不调用付费 API 的离线评测：

```powershell
python evals\production-delivery-orchestrator\run_evals.py --self-test
python evals\production-delivery-orchestrator\run_evals.py --report-prefix latest
```

默认基线直接读取 Git 提交 `b3d9a17` 中已发布的技能，不需要检出旧版本。评测会检查 frontmatter、触发边界、渐进披露、模糊请求侦察、权限、验证诚实性、独立审查、工作区保护和默认上下文代理，并生成 JSON 与 Markdown 报告。场景表只标记 `COVERED/UNCOVERED` 的静态规则映射，不会把未执行的 prompt 写成 PASS；`cases.yaml` 的 `must/must_not` 目前是设计规格，不代表 19 个场景都已由真实 Agent 逐项执行。

故意使用已知坏候选时，runner 应返回非零退出：

```powershell
python evals\production-delivery-orchestrator\run_evals.py `
  --candidate evals\production-delivery-orchestrator\baselines\legacy-monolithic-proxy.md `
  --report-prefix known-bad
```

`fixtures/video-polling-state-machine` 是一个故意保留 `failed` 状态不停止轮询的最小仓库，用于证明侦察器能识别提交、入队、处理、轮询、终态和结果展示链路。它的回归测试在未修复 fixture 时预期失败。

这些评测是离线静态与行为代理，不调用真实 LLM，也不能单独证明任意模型、客户端或未来版本一定遵守技能。发布前仍需使用新上下文做真实 forward-test，并进行独立只读审查。

本仓库还提供可配置真实 Agent/CLI 的 forward-test harness：

```powershell
python evals\production-delivery-orchestrator\run_forward_tests.py --self-test
python evals\production-delivery-orchestrator\run_client_matrix.py
```

`--self-test` 只使用本地合成 helper 验证 harness，不是模型行为证据。`run_client_matrix.py` 默认也只探测本机客户端，不会调用模型，结果必为 `NOT_RUN`。当前注册表包含基于本机 `--help` 核对的 Codex CLI、Claude Code 和 Gemini CLI 命令模板；Windows 使用 `.cmd`，Linux/macOS 使用无后缀命令。若探测版本与 registry 记录不一致，矩阵会标记 `VERSION_MISMATCH` 并拒绝发起真实样本，先更新并复测该命令模板。

要真实采集某个客户端的新证据，必须显式执行 `--execute --allow-unsafe-host-execution`。第二个开关故意使用危险名称：runner 会使用临时 fixture、临时 HOME、最小子进程环境和临时技能副本，但它**不能**把 Claude Code 或 Gemini CLI 变成 OS/容器沙箱。生产样本应在你控制的 VM、容器或专用测试账号中运行。这可能消耗订阅额度或 API 配额：

```powershell
python evals\production-delivery-orchestrator\run_client_matrix.py `
  --clients claude-code `
  --execute `
  --allow-unsafe-host-execution
```

一次矩阵运行会为每个客户端写出独立的 JSON/Markdown 报告，以及汇总 `client-matrix.json`。每轮会把完整技能复制到 fixture 后再执行，并检测副本是否被 Agent 修改；runner 不继承宿主的 API Key、云凭据或用户 HOME。确有必要时，通过 `--agent-env-file` 提供最小 `KEY=VALUE` 集合；其值会从落盘报告脱敏。报告记录执行前后完整技能 artifact SHA-256；只要技能内容或路径变化，旧样本就不会被当成当前版本证据。哈希会把 UTF-8 文本的 CRLF/CR 统一为 LF，但保持二进制原始字节，因此 Windows/Linux checkout 可比较且不会掩盖真实内容变化。

`reports/forward-tests.json` 中的两次 Codex 子任务记录是 `v1.0.1` 对应 artifact 的历史证据，不是 Claude Code、Gemini 或当前工作树的行为结论。修改技能后用 `--verify-record` 验证该文件应失败并提示陈旧；只有在当前 artifact 上重新运行真实 CLI 才能产生新的 PASS 证据。没有 `--agent-command` 的低层 harness 仍会退出 `2` 并标记 `NOT_RUN`，不会伪造 PASS；自定义客户端可继续直接传入命令模板。

仓库的 GitHub Actions 会在 Windows 和 Linux 上运行同一组自测、真实 Git 基线对照、已知坏候选阻断、forward-test harness/矩阵配置与脱敏安全测试、真实临时安装集成测试和空白错误检查；不会在 CI 中消耗模型额度生成新的真实样本。

## 常见问题

### 安装后没有自动触发怎么办？

1. 新开任务或重启对应 CLI；
2. 检查整个技能目录是否已安装；
3. 显式指定 `$production-delivery-orchestrator` 或技能名；
4. 如果工具没有原生技能发现，生成对应项目规则桥接；
5. 检查目标工具当前版本的技能目录和规则文件格式。

### 桥接是否会让每个请求都加载长协议？

不会。桥接只在请求匹配生产交付、复杂修复、审查或模糊故障侦察时引导工具读取 `SKILL.md`，并明确要求 references 按需加载。

### 可以只复制 `SKILL.md` 吗？

不建议。`SKILL.md` 会根据任务引用 `references/`，完整目录才是可用的技能包。

### 安装器会覆盖已有规则文件吗？

不会覆盖文件其他内容。桥接使用受管标记更新自己的区块；标记损坏时会停止并报错。技能目标目录已存在时也会默认停止，只有显式 `--force` 才替换安装副本。

## 仓库结构

```text
Agent-skills-code-op/
├── README.md
├── LICENSE
├── docs/
│   ├── project-benchmark-analysis.md
│   └── reference-scan-report.md
├── reviews/
│   └── final-critic.md
├── workflow_status.md
├── evals/
│   └── production-delivery-orchestrator/
│       ├── tests/
│       ├── fixtures/
│       └── reports/
└── skills/
    └── production-delivery-orchestrator/
        ├── SKILL.md
        ├── agents/
        ├── references/
        └── scripts/
            └── install_skill.py
```

## 许可证

本项目使用 [Apache License 2.0](LICENSE)。
