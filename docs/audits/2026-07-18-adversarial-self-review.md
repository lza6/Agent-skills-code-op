# 反向审判：本轮工作最容易自欺的地方（2026-07-18）

这不是通过结论。它是主线程在要求独立 Critic 前，对自身工作做的最强反驳。只要一项没有
代码、命令或可复查文档证据，就不能写成闭环。

| 反驳 | 具体风险/影响 | 处理状态与证据 | 仍需动作 |
|---|---|---|---|
| 可能把单 Skill 仓库误当 SaaS 而制造无关代码 | 无用 UI/API/数据库会扩大攻击面、依赖与维护成本 | 已排除；目录、CI、入口和 threat model 一致确认没有此运行面 | Critic 复核 `not_applicable` 是否有证据。 |
| 可能把“文档已写”当成行为修复 | 文档、HTML、mock 或静态 grep 无法修安装/评测 | Windows console、baseline preflight 均有生产代码与回归；HTML 有真实浏览器旅程 | 重跑全套后让 Reviewer 看实际 diff。 |
| 历史测试数/Release 可能被冒充为本轮结果 | 发布判断错误，调用者得到虚假兼容声明 | `test-ledger` 只列本轮命令，current-state 明确三 CLI `partial` | 最终提交前再跑 diff/check 与 tag/ref。 |
| 新维护契约可能只是没人读取的 Markdown | 未来 Agent 仍会先改后看 | SKILL 条件路由、独立 contract 测试、evaluator capability 负向测试均已加入 | Critic 验证路由不会强迫 Quick 任务加载。 |
| 浏览器测验按钮可能只是视觉占位 | 用户点击没有反馈或评分错误 | Playwright 实测时发现测试自身 4/5 vs 3/5 断言错误，已修；现已实测失败、通过、重置 | 独立 Reviewer 再跑同一旅程。 |
| CLI 工具“能发现”可能不等于在 Windows 中文路径可用 | `gh-fix-ci` 原脚本把 Git root 错解码，运行直接崩溃 | 本机 global skill 的 Git/GH text subprocess 显式 UTF-8 后，查询到真实 no-PR 结果 | 该修复不在本仓库版本控制内，外部技能升级可能覆盖它。 |
| 实际 Agent matrix 可能被离线 100 分掩盖 | 用户误以为 Claude/Gemini 已验证 | 每个报告和状态都写明 Codex 3/3、Claude 无模型、Gemini 无隔离凭证 | 提供短期受控凭证后执行三案例，才可关闭。 |
| 临时制品可能污染工作区或被误提交 | 发布内容污染、泄漏本地路径 | 根 `.gitignore` 明确排除 `.matrix-audit/`、`.release-audit/` 和 `.codegraph/` 本地缓存 | Critic 确认忽略规则只匹配本地生成物，不吞掉项目源文件。 |
| “独立审查”可能只是主线程复述 | 自签收掩盖盲点 | 已有只读 reviewer 历史结论，但本轮新增 diff 尚未复审 | 必须派发最终独立只读审查；有发现则修复并让同一 reviewer 复验。 |

## 当前分级

- **P0：0（待独立复验）**。本轮已执行的入口、测试、release 构建和浏览器交互没有 P0。
- **P1：0（待独立复验）**。当前最接近 P1 的真实外部边界是 Claude/Gemini 凭证/模型，已明确为外部阻塞，而不是掩盖成通过。
- **P2：0（待独立复验）**。本地验证/索引目录已由根 `.gitignore` 明确排除，不再作为待提交污点。
- **P3：1**。Understand Anything 的图谱生成受当前 Windows sandbox 限制；安装/构建成功不替代图谱成功，也不影响核心安装/评测/发布路径。
