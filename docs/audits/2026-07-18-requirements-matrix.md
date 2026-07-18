# 生产审计需求追踪矩阵（2026-07-18）

本矩阵只描述当前 `001-production-audit` 变更。稳定发布事实的唯一入口是
[current-state](../current-state.md)；历史 Release 与历史审计不构成当前运行证明。

| 需求 | 实现/证据位置 | 状态 | 缺口或下一步 |
|---|---|---|---|
| 修改前有可恢复规格、计划、依赖与验收 | `.specify/`、`specs/001-production-audit/`、`task_plan.md`、`workflow_status.md` | 已闭环 | 每个后续 Deep 变更都要建立独立规格或更新现有任务。 |
| 当前事实不被历史文档覆盖 | `docs/current-state.md`、`docs/codebase/CONCERNS.md`、`reviews/final-critic.md`、`test_current_state.py` | 已闭环 | 版本、CLI 证据或支持范围变化时更新回归断言。 |
| Windows 消费者可读的安装器帮助 | `scripts/install_skill.py`、`test_install_skill.py` | 已闭环 | 仅保证有 `reconfigure` 的文本流；不可控制宿主终端字体。 |
| 浅克隆/Source archive 评测失败可恢复 | `run_evals.py`、`test_run_evals.py`、README、`support-matrix.json` | 已闭环 | 需要历史或显式 `--baseline`；不提供不安全的自动 fallback。 |
| 新任务先判断文档/规则/记忆是否过时 | `references/maintenance-contract.md`、SKILL 路由、`test_maintenance_contract.py` | 已闭环 | 外部记忆不是事实源，仍须本轮命令核对。 |
| 用户要求的技能/外部工具被逐项盘点 | [skill-tool-applicability](2026-07-18-skill-tool-applicability.md) | 已闭环 | 只把适用的能力带入项目；Figma/Composio 仍需真实项目输入与凭证。 |
| 安全边界和攻击面审计 | [threat model](2026-07-18-threat-model.md) | 已闭环 | 若分发渠道、权限模型或安装器文件边界变化，重新建模。 |
| 交接说明和可评分理解测验 | [HTML report](../reports/production-audit-closure-2026-07-18.html)、`test_production_audit_report.py` | 已闭环 | 浏览器旅程依赖本机 Playwright/browser；结果在测试台账中如实列出。 |
| 独立六维审查、修复、复验 | `reviews/`、`workflow_status.md`、本矩阵所列回归 | 部分闭环 | 本轮新增合同/报告的最终独立复验必须在全量测试后完成。 |
| 三客户端真实 Agent 行为 | `docs/current-state.md`、`workflow_status.md` | 外部阻塞 | Codex 3/3 PASS；Claude 无可用模型，Gemini 无隔离凭证。不可由离线 eval 替代。 |
| 前端、后端 API、数据库、容器、支付、SaaS UI | 仓库结构与 [project facts](../project-benchmark-revalidation-2026-07-18.md) | 不适用 | 这是离线 Python Skill 分发仓库；不得为了检查表制造不存在的产品面。 |
