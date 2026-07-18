# 生产审计测试台账（2026-07-18）

本文件只记录本次审计产生或复跑的证据。命令尚未执行前必须写为 `pending`；不得从历史
报告复制为“本轮通过”。本机是 Windows；Linux 专用子进程清理回归在本机被明确 skip。

| 层级 | 命令/场景 | 当前状态 | 说明 |
|---|---|---|---|
| TDD | maintenance contract + HTML report 新测试 | PASS | 先得到预期 1 fail + 3 errors；实现后 4/4 PASS。 |
| 规格 | Spec Kit traceability/任务依赖 | PASS | `specify 0.12.16` 可用；FR-001–010 均映射，唯一未闭合项仅等待最终独立复验/tag 检查。 |
| 单元 | installer + maintenance contract | PASS | `python -m unittest discover -s skills/production-delivery-orchestrator/tests ...`：29/29。 |
| 单元 | evaluator/forward/client matrix | PASS（2 skip） | 64/64 通过；新 maintenance freshness 负向回归已纳入评测门，两项 Linux subreaper 测试在 Windows 显式 skip。 |
| 治理 | `.github/workflows/tests` | PASS | 19/19：Actions SHA、凭证模式、quality gate、当前事实和支持矩阵。 |
| 工具 | `tools/tests` | PASS | 6/6：HTML 结构/本地链接及 coverage 基线工具。 |
| 集成 | registry 与 dependency inventory | PASS | `build_skill_registry.py --check`、`generate_dependency_inventory.py --check` 均一致；registry suite 5/5。 |
| 集成 | Release build/verify | PASS | release suite 7/7；临时本地 v1.7.0 制品 build + verify 通过，未移动 tag。 |
| 离线行为 | eval self-test / forward self-test | PASS | eval 报告 `llm_calls: 0`；forward 3/3 为明确 synthetic，不冒充真实 Agent。 |
| 浏览器 | 本地 HTML quiz 正确/错误路径 | PASS | `webapp-testing` 的 server wrapper + headless Playwright：3/5 失败时两道错题均显示正确选项+说明、4/5 通过、reset 均实测。 |
| 客户端 probe | `run_client_matrix.py` 无 `--execute` | NOT_RUN（预期） | 生成三 profile probe 报告但不启动 Agent；没有凭证/模型时不把 probe 当成功。 |
| 导航 | CodeGraph 本地索引与符号查询 | PASS | `init --index` 后 `sync .`；27 files、773 nodes、1,286 edges，`InstallTransaction` 查询命中定义和事务方法。 |
| 独立审查 | 同一只读 Critic 初审→修复→复验 | APPROVE | 四项 Required 均修复；六维结论见 `reviews/production-audit-closure-review-2026-07-18.md`。 |
| 外部 CLI | Codex/Claude/Gemini 真实行为矩阵 | partial | 历史新鲜事实：Codex 3/3 PASS；Claude 无可用模型；Gemini 无隔离凭证。 |

质量命令中一次误将 `--self-test` 传给不支持该参数的 `run_client_matrix.py`，已停止重试并改为
其真实支持的无执行 probe，得到预期 `NOT_RUN`。`.matrix-audit/`、`.release-audit/` 和
`.codegraph/` 是本地生成缓存，已经在根 `.gitignore` 明确排除；它们不进入提交，也不会让工作树
因验证产物持续变脏。
