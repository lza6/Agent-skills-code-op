# Production Delivery Orchestrator 真实 Forward-test 记录

- 日期：`2026-07-17`（Asia/Shanghai）
- 客户端：`Codex desktop collaboration subagents`
- 上下文：两个 Agent 均使用 `fork_turns=none` 新上下文
- 模型与采样配置：运行时未暴露，记录为 `unknown`
- 结论：**PASS**

> 这是两次真实 Agent 执行的持久记录，不是离线关键词评分。完整技能 artifact SHA-256 在两个 fresh-context 任务启动前计算，并在主线程复验后确认未变化；协作运行时仍未提供精确模型/采样配置或可下载的完整工具 trace。后续可用 `run_forward_tests.py --agent-command ...` 自动捕获 CLI、stdout/stderr、测试退出码和工作树差异。

- 完整技能 artifact SHA-256：`2213242cdec0f8afcfc531ab6b2a7633136b7e6b521c2d5bdde20257eed9a6e7`

## PASS：模糊修复请求

- Prompt：`帮我修复视频任务问题。`
- Agent：`/root/forward_current_vague_fix`
- Fixture 基线：`9ca54e9697844aa9f39c17a9aa79af58acad15a5`
- 行为：先扫描仓库和状态契约，没有要求用户指定文件、测试或库；识别后端 `failed` 是终态而前端仍轮询。
- 修改：只把 `frontend/useVideoJob.ts` 的终态集合从 `['completed']` 改为 `['completed', 'failed']`。
- 主线程复验：`python -m unittest discover -s tests -v` 退出 `0`；`git diff --check` 退出 `0`；仅一个文件变化。
- 限制：最小 fixture 没有完整 React 构建和浏览器 E2E；`tsc` 不可用，Agent 使用 Node v25.8.1 直接加载 TypeScript 模块验证轮询判定。

## PASS：只分析、不修改

- Prompt：`审查视频任务为什么会无限轮询，先不要修改代码。`
- Agent：`/root/forward_current_analysis_only`
- Fixture 基线：`9ca54e9697844aa9f39c17a9aa79af58acad15a5`
- 行为：给出相同的前后端终态不一致根因，并运行只读契约测试与搜索。
- 主线程复验：`git status` 为空；未暂存与暂存 diff 均为空。
- 限制：fixture 没有真实定时器、API、队列、数据库或外部视频服务。

## 可重复运行

验证 harness 自身：

```powershell
python evals\production-delivery-orchestrator\run_forward_tests.py --self-test
```

验证本记录结构：

```powershell
python evals\production-delivery-orchestrator\run_forward_tests.py `
  --verify-record evals\production-delivery-orchestrator\reports\forward-tests.json
```

没有显式 `--agent-command` 时，脚本返回 `NOT_RUN`/退出码 `2`，不会把未执行的真实 Agent 测试写成 PASS。
