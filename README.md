# Agent Skills Code OP：一人团队式生产交付技能

`production-delivery-orchestrator` 是一个面向软件开发智能体的通用 Agent Skill。

它不是简单的“编码规则清单”，而是一套从需求对齐、仓库侦察、方案设计、编码实现、测试验证、独立审查到最终交付的生产级工作契约。

核心目标是：

> 让用户像老板或产品负责人一样决定“最后要看到什么结果”，技术路径、代码组织和验证方式由智能体根据真实仓库自主完成。

## 核心能力

- 对软件、前端、后端、API、数据库、SaaS、AI Agent、DevOps 等开发任务自动触发。
- 完整加载长系统提示词，不把生产交付规则压缩成空洞摘要。
- 先识别用户最终要获得的产物、用户旅程和 MUST 验收标准。
- 只在选择会实质改变结果、风险、数据、成本或范围时询问用户。
- 询问时提供两到三个结果选项，推荐项放在第一个。
- 自动区分 Quick、Standard 和 Deep 任务，避免简单任务过度流程化。
- 区分“只分析”和“授权修改”，不会因为用户说“审查”就擅自改代码。
- 保护工作区和用户未提交改动，禁止静默重置或覆盖。
- 要求真实执行测试、类型检查、Lint、构建、渲染或等价验证。
- 禁止把 Mock、TODO、占位、理论方案或未执行的命令冒充已交付结果。
- 对生产写入、外部操作、付费 API、部署、推送和破坏性操作保留确认边界。
- 按任务风险启用安全、性能、并发、多租户、计费、UI/UX、CI/CD 和可观测性门禁。
- 在完成前执行盲点扫描、独立审查和验收收敛。

## 工作方式

```text
用户请求
  ↓
技能根据 description 自动触发
  ↓
完整读取 system-prompt.md
  ↓
判断最终结果是否清晰
  ├─ 已清晰：直接侦察、计划、实现和验证
  └─ 不清晰：提供结果选项，让用户决定产品结果
  ↓
根据 Quick / Standard / Deep 执行对应交付闭环
  ↓
真实验证、审查、文档同步和最终交付
```

## 推荐安装方式

本仓库遵循通用 [Agent Skills 规范](https://agentskills.io)，推荐使用开放技能安装器 [`npx skills`](https://github.com/vercel-labs/skills)。

`npx skills` 可自动识别 Claude Code、Codex、Cursor、Gemini CLI、GitHub Copilot、Windsurf、Cline、Roo Code、OpenCode 等大量智能体的技能目录。

### 交互式安装

```bash
npx skills add lza6/Agent-skills-code-op
```

安装器会识别仓库中的 `production-delivery-orchestrator`，并让你选择安装范围、目标智能体以及链接或复制方式。

### 全局安装到 Codex 和 Claude Code

```bash
npx skills add lza6/Agent-skills-code-op \
  --skill production-delivery-orchestrator \
  --global \
  --agent codex \
  --agent claude-code
```

PowerShell 也可写成单行：

```powershell
npx skills add lza6/Agent-skills-code-op --skill production-delivery-orchestrator --global --agent codex --agent claude-code
```

如果 Windows PowerShell 因执行策略拦截 `npx.ps1`，使用 `npx.cmd` 即可，不需要修改系统执行策略：

```powershell
npx.cmd skills add lza6/Agent-skills-code-op --skill production-delivery-orchestrator --global --agent codex --agent claude-code
```

### 安装到当前项目

在目标项目根目录执行：

```bash
npx skills add lza6/Agent-skills-code-op \
  --skill production-delivery-orchestrator \
  --agent codex \
  --agent claude-code
```

项目级安装适合将技能与仓库一起管理，也便于团队成员使用相同规则。

### 查看仓库中可安装的技能

```bash
npx skills add lza6/Agent-skills-code-op --list
```

### 更新

```bash
npx skills update --global production-delivery-orchestrator
```

### 卸载

```bash
npx skills remove --global production-delivery-orchestrator
```

## 通过 Codex 内置 skill-installer 安装

也可以直接对 Codex 说：

```text
使用 skill-installer 从下面的 GitHub 路径安装技能：
https://github.com/lza6/Agent-skills-code-op/tree/main/skills/production-delivery-orchestrator
```

Codex 会将它安装到 `$CODEX_HOME/skills/production-delivery-orchestrator`；当没有设置 `$CODEX_HOME` 时，默认使用 `~/.codex/skills/production-delivery-orchestrator`。

## 手动复制安装

如果不使用安装器，必须复制整个技能目录，不能只复制 `SKILL.md`。

| 工具 | 全局安装目录 | 项目级安装目录 |
|---|---|---|
| Codex | `~/.codex/skills/production-delivery-orchestrator/` | `.agents/skills/production-delivery-orchestrator/` |
| Claude Code | `~/.claude/skills/production-delivery-orchestrator/` | `.claude/skills/production-delivery-orchestrator/` |
| Cursor | `~/.cursor/skills/production-delivery-orchestrator/` | `.agents/skills/production-delivery-orchestrator/` |
| Gemini CLI | `~/.gemini/skills/production-delivery-orchestrator/` | `.agents/skills/production-delivery-orchestrator/` |
| GitHub Copilot | `~/.copilot/skills/production-delivery-orchestrator/` | `.agents/skills/production-delivery-orchestrator/` |
| 通用 Agent Skills | 根据工具自身目录 | `.agents/skills/production-delivery-orchestrator/` |

技能目录必须保持以下结构：

```text
production-delivery-orchestrator/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── outcome-contract.md
│   └── system-prompt.md
└── scripts/
    └── install_skill.py
```

## 自带 Python 安装器

仓库中还保留了一个不依赖 Node.js 的 Python 安装器，主要用于离线环境、手动安装或生成项目指令桥接。

```bash
git clone https://github.com/lza6/Agent-skills-code-op.git
cd Agent-skills-code-op/skills/production-delivery-orchestrator
python scripts/install_skill.py --scope user --targets all
```

为某个项目同时生成 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、Cursor、Windsurf 和 Cline 桥接：

```bash
python scripts/install_skill.py \
  --scope project \
  --project-dir /path/to/project \
  --targets all \
  --bridges all
```

为其他工具指定自定义项目规则文件：

```bash
python scripts/install_skill.py \
  --scope project \
  --project-dir /path/to/project \
  --targets agents \
  --custom-bridge .other-agent/rules.md
```

## 安装后怎么使用

### 自动触发

安装后，在新一轮任务或重启对应编码智能体后，直接描述真实需求：

```text
帮我修复视频生成任务失败后仍会无限轮询的问题，
并把失败、超时、重试和重复提交整个链路做完。
```

技能的 `description` 会尽可能匹配软件开发、修复、审查、测试、架构和生产交付类任务。

### 显式调用

如果当前工具支持显式技能名，可以说：

```text
使用 $production-delivery-orchestrator 将这个需求推进到可验证的最终交付。
```

或者：

```text
启用 production-delivery-orchestrator，先确认用户最后会看到什么结果，然后直接落地。
```

### 需求模糊时的预期行为

如果用户只说：

```text
帮我把这个项目做好。
```

技能不应立即追问使用哪个库、文件怎么分层，而应优先询问结果层级：

1. **直接完成生产级落地（推荐）**：修复或实现核心用户旅程，包括测试、失败路径和文档，但不擅自部署生产。
2. **先做全面审查**：只输出问题、根因、风险和修复优先级，不改代码。
3. **先做方案或原型**：先交付规格、架构或可演示版本，不宣称已经达到生产标准。

## 关于长系统提示词

本技能的实际生效规则位于：

```text
skills/production-delivery-orchestrator/references/system-prompt.md
```

该文件最初来自 `GPT5.6全栈规则提示词（codex版）.txt`，但不是简单原样覆盖。为了真正适配 Claude Code、Codex 和其他 Agent Skills 工具，通用版做了以下必要调整：

- 将“运行在 OpenAI Codex 中”改为“运行在当前智能体编码工具、CLI 或 IDE 中”。
- 将只识别 `AGENTS.md` 改为同时兼容 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` 和工具专用规则。
- 删除只在原作者电脑上存在的绝对路径，改成读取用户明确提供的本地规则。
- 加入“老板式结果对齐”，让用户决定产品结果，技术细节由智能体负责。
- 保留原始长协议的所有主要章节，没有把它压缩成短提示词。

### 是否应该直接用原始 TXT 覆盖它？

**如果只为 Codex 一个工具服务，可以；但对这个跨工具仓库来说，不建议。**

直接覆盖会重新引入 Codex 专属角色、单一规则文件假设以及不可移植的本地绝对路径。当前的 `system-prompt.md` 已经是“完整长规则＋跨平台适配”版，更适合作为仓库的默认生效规则。

## 仓库结构

```text
Agent-skills-code-op/
├── README.md
├── LICENSE
└── skills/
    └── production-delivery-orchestrator/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        ├── references/
        │   ├── outcome-contract.md
        │   └── system-prompt.md
        └── scripts/
            └── install_skill.py
```

## 常见问题

### 安装后没有自动触发

1. 新建一轮任务或重启当前智能体。
2. 检查安装目录中是否存在完整的 `SKILL.md`、`references/` 和 `scripts/`。
3. 检查 `SKILL.md` 顶部的 `name` 和 `description` 是否为有效 YAML。
4. 使用“启用 production-delivery-orchestrator”进行一次显式调用。
5. 部分工具只在新会话扫描新安装的技能。

### 是否会对每个问题都加载长提示词？

原生 Agent Skills 工具通常先使用 `name` 和 `description` 做轻量匹配，匹配成功后才加载 `SKILL.md` 和完整系统提示词。

如果将技能写入始终生效的 `AGENTS.md` 或工具规则桥接，则该项目的每个软件任务都会被要求读取它。

### 技能会自动部署或调用付费 API 吗？

不会。默认交付协议要求对生产部署、真实外部写入、付费 API、推送、合并和破坏性操作先获得明确授权。

### 是否可以只复制 `SKILL.md`？

不可以。`SKILL.md` 会强制读取 `references/system-prompt.md`，因此必须安装完整目录。

## 许可证

本项目使用 [Apache License 2.0](LICENSE)。
