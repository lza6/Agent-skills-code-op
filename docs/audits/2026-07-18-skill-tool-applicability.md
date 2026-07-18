# 请求技能与外部工具的适用性审计（2026-07-18）

“目录存在”只证明可发现；“调用成功”只证明入口可运行；两者都不证明真实 Agent
行为、产品质量或生产可用性。本表把三者分开记录。

| 能力 | 本机/来源状态 | 本次最小调用或验证 | 对当前仓库的适用结论 |
|---|---|---|---|
| `create-plan` | 已在 Codex/Agents/Claude 技能根发现 | 已读取其只读计划契约；现有 Spec Kit/`task_plan.md` 是实际计划载体 | 适用：用于先计划；不在实现阶段取代已获授权的开发工作。 |
| `planning-with-files` | 已安装 | 已读取并使用 `task_plan.md`、`findings.md`、`progress.md`；`check-complete.sh` 已执行 | 适用：长链路审计的可恢复状态。 |
| Spec Kit | `specify 0.12.16`；官方 `github/spec-kit@57cc518d` | 已建立 constitution、spec、plan、traceability、tasks | 适用：本轮复杂变更的规格化基础。 |
| `frontend-skill` / `frontend-design` | 前者是已弃用上游的目录提示；后者已安装 | 已读取能力边界 | 不适用：仓库没有 Web UI；不把“高级前端”伪造为本仓库需求。 |
| `figma-implement-design` | 已安装，但没有 Figma URL/node 或 MCP OAuth | `codex.cmd mcp get figma` 确认未配置，已读取前置条件 | 不适用：无设计稿、无前端组件、无 Figma 连接。 |
| `webapp-testing` | 已安装 | `with_server.py --help` 和 headless Playwright HTML 报告 fail/pass/reset journey 已执行 | 部分适用：仅用于本次静态交接报告，不代表仓库存在产品 E2E。 |
| `gh-fix-ci` | 已安装，`gh` CLI 已认证 | 原脚本在中文路径下把 Git 根错误解码为无效 cwd；将其 `git/gh` text subprocess 固定为 UTF-8 后，实际查询返回“当前 branch 无 PR” | 部分适用：工具已可在此 Windows 路径运行；当前没有待修 PR 失败。 |
| `security-threat-model` | 已安装 | 已按仓库边界输出 [威胁模型](2026-07-18-threat-model.md) | 适用：安装、评测、Release 和 CLI 宿主隔离是实际攻击面。 |
| `mcp-builder` | 已安装 | `codex.cmd mcp list` 确认已有外部 server 配置、但本仓库没有 server | 不适用：没有 MCP Server 需求；强行新增服务会扩大供应链和维护面。 |
| `cli-creator` | 已安装 | `install_skill.py --help` 已实际调用 | 不适用：现有 stdlib CLI 已是清晰的单用途命令；不另造 wrapper。 |
| `pr-review` | 已安装 | 实际结构校验返回 0 errors、2 warnings（第三方期望的 license/metadata） | 部分适用：其规则面向另一技能仓库；不为消除非规范 warning 破坏本仓库只含 `name`/`description` 的标准 frontmatter。 |
| `composio-connect` | 未找到同名本地技能；Composio 是 API-key/OAuth SDK | 已核验官方来源 `ComposioHQ/composio@c34401e` | 不安装：当前无外部 SaaS 集成；引入 OAuth/凭证没有收益。 |
| `addyosmani/agent-skills` | 上游固定到 `06300e258ef62cdbfbc9b1615ac5b4f58bee05ac` | `npx skills` 对 commit SHA 当 branch 的解析失败，未写入 | 不重复安装：本机已有匹配能力；失败不被写成成功。 |
| `obra/superpowers` | 上游固定到 `d884ae04edebef577e82ff7c4e143debd0bbec99`；相关方法技能已在本机 | 本轮按计划、TDD、分工、独立审查流程使用 | 适用为方法论，不添加第二套项目运行时。 |
| `awesome-llm-apps` | 上游固定到 `41621a5735d573ce6d7d57def504fce873f18e4f` | 已按目录定位：是应用模板集合，不是安装器技能 | 不安装：当前产品是 Skill 分发系统；未来真实 AI 产品可选其 `agent_skills/`。 |
| Understand Anything | 固定源码 `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`，已在 `%USERPROFILE%\\.understand-anything` 安装/构建并建技能链接 | `pnpm install --frozen-lockfile` 与 core build 成功；图谱生成尝试受 Windows sandbox `os error 206` 阻塞 | 仅安装/构建验证成功；没有 `.ua` 图谱，不把它说成代码理解或运行验证成功。 |
| CodeGraph 本地索引 | 本机 `codegraph 0.9.3`；Codex MCP 已登记 `codegraph serve --mcp` | `codegraph init --index .` 后又执行 `sync .`；当前索引 27 文件、773 nodes、1,286 edges，`InstallTransaction` 查询返回定义/事务方法 | 适用为本地、无模型代码导航证据；索引缓存 `.codegraph/` 被 Git 忽略，不能替代行为/安全/Release 验证。 |

外部来源在未来重试前必须重新核验固定 commit、安装脚本、写入路径、权限和版本；不要用浮动
`main` 或已弃用目录作为新供应链。
