# 独立 Critic 六维审查与复验

## 已发布闭环与当前增量状态

- 独立审查者：`/root/final_critic_completion_audit`
- 审查方式：独立上下文、只读；复现工件写入系统临时目录，不修改审查对象
- 首轮 Verdict：`Request Changes`
- 首轮问题：P0 `0`，P1 `2`，P2 `2`，P3 `1`
- 原 Critic 复验 Verdict：`Approve`
- 首次最终推送 CI 修复复验 Verdict：`Approve`
- 已发布 `v1.0.0` 闭环未关闭问题：P0 `0`，P1 `0`
- N12 增量审计 Verdict：`Request Changes`
- N12 当前未关闭：P0 `0`，P1 `2`，P2 `2`

本文件持久化原始需求完整性、逻辑正确性、边界情况、代码质量、测试覆盖和实际运行结果六个维度的审查闭环。历史 `Approve` 只证明 `v1.0.0` 当时范围没有阻塞 P0/P1；本轮发现新的报告准确性缺口后，整体状态已重新打开为 `needs_fix`，不能沿用历史 `Approve` 代替 N12 复验。

## 一、首轮发现

| ID | 等级 | 发现 | 首轮证据 | 首轮状态 |
|---|---|---|---|---|
| F1 | P1 | 项目级 native 安装可经 `.agents/.codex/.claude` 父目录 symlink 写出项目根 | `.agents -> outside` 后安装退出 `0`，项目外创建技能 | Open |
| F2 | P1 | Forward 记录只绑定 `SKILL.md`，routed reference 变化后仍 PASS | 修改 `references/discovery-contract.md` 后 verify-record 退出 `0` | Open |
| F3 | P2 | README 链接的最终审查文件尚不存在 | `reviews/final-critic.md` 缺失 | 本文件关闭 |
| F4 | P2 | 19 个 `cases.yaml` 场景多数仍是静态映射，`must/must_not` 未逐项执行 | 只有两个真实 Agent forward 场景 | 接受并披露 |
| F5 | P3 | 分析报告中的文件数、runner 行数和测试数已滞后 | 报告仍写 34 文件、约 703 行、4 项安装测试 | 文档同步关闭 |

## 二、Builder 修复映射

### F1：项目级 native 安装边界

- 修复提交：`bef6b20`
- 文件：
  - `skills/production-delivery-orchestrator/scripts/install_skill.py`
  - `skills/production-delivery-orchestrator/tests/test_install_skill.py`
- 实现：项目级 native destination 在复制前解析真实路径，并验证仍位于 `project_dir`；桥接复用同一项目边界判断。
- 回归：
  - `.agents` 普通安装越界拒绝；
  - `.codex --force` 越界拒绝且外部 sentinel 不变；
  - `.claude --dry-run` 越界仍失败；
  - `--targets all` 在预检阶段失败且没有部分安装；
  - user scope 三个目录继续可用。

### F2：Forward 完整 artifact 新鲜度

- 修复提交：`bef6b20`
- 文件：
  - `evals/production-delivery-orchestrator/run_forward_tests.py`
  - `evals/production-delivery-orchestrator/tests/test_forward_tests.py`
  - `evals/production-delivery-orchestrator/reports/forward-tests.json`
  - `evals/production-delivery-orchestrator/reports/forward-tests.md`
- 实现：
  - 对完整技能目录的普通文件按相对 POSIX 路径排序；
  - 严格 UTF-8 且无 NUL 的文本统一 `CRLF/CR → LF`，二进制保持原始字节；
  - 使用 artifact v2 domain、文本/二进制 kind、路径长度、路径、内容长度和内容生成确定性 SHA-256；
  - 排除 `__pycache__`、`.pyc`、`.DS_Store`；
  - artifact 中的文件或目录 symlink 采用 fail-closed；
  - 执行时、记录时和当前 artifact hash 必须有效且完全一致；
  - `unavailable` 不再能作为严格 PASS 证据。
- 回归：reference 内容修改、新增、删除、重命名都会使旧记录失败；缓存文件不改变 hash。

### 新鲜真实 forward-test

两个 Agent 均使用 `fork_turns=none`，只获得技能路径、隔离 fixture 和原始用户请求，没有获得预期根因或修复答案。

| Case | Agent | 结果 | 主线程证据 |
|---|---|---|---|
| `帮我修复视频任务问题。` | `/root/forward_canonical_vague_fix` | 只修改 `frontend/useVideoJob.ts`，把 `failed` 加入前端终态 | 修复后 unittest 退出 `0`；diff check `0`；仅一个文件变化 |
| `审查视频任务为什么会无限轮询，先不要修改代码。` | `/root/forward_canonical_analysis_only` | 识别前后端终态不一致，保持只读 | fixture 契约测试按预期 RED；git status/diff 均干净 |

- Fixture baseline：`05947fbd60c06667a5038b89bfa0641cd5ce0a13`
- 执行前后完整技能 canonical artifact SHA-256：`02c952410f03be6d1df86cf406d3cf1d5fbd115906cf6565651b5184a8718458`
- 精确模型、采样配置和可下载原始工具 trace 未由协作运行时暴露，已在 forward 报告中披露。

## 三、同一 Critic 复验

### F1 — Closed

原攻击路径重放：

```text
project/.agents -> outside
python install_skill.py --scope project --project-dir <project> --targets agents
```

复验结果：

```text
installer exit: 1
错误：安装目标越出了项目目录
outside_skill_created: false
```

normal、`--force`、`--dry-run`、all-target 原子预检和 user scope 回归均通过；本机相关 symlink 测试没有 skip。

### F2 — Closed

| 复验场景 | 退出码 | 结果 |
|---|---:|---|
| 当前匹配记录 | 0 | PASS |
| 修改 `references/discovery-contract.md` 后验证旧记录 | 1 | FAIL，hash 陈旧 |
| 执行时 hash 改为 `unavailable ...` | 1 | FAIL，不允许作为严格证据 |

同一 Critic 确认当前 artifact hash 与记录一致，且没有由修复引入新的 P0/P1。

## 四、六维验收结论

1. **需求完整性**：原始 1–9 项目识别、参考筛选、差距、迁移、路线图、实施前影响/验证/回滚、未知项和多 Agent 闭环均有持久证据。
2. **逻辑正确性**：技能状态机、授权路由、legacy exclusion、安装与 forward 证据逻辑一致；F1/F2 已关闭。
3. **边界情况**：桥接/native symlink、marker、dry-run、force、脱敏、timeout、记录篡改、reference 陈旧和 legacy 代打均有适用验证。
4. **代码质量**：边界函数和 artifact hash 职责明确；保留 eval runner 多职责和多目标全局事务两个非阻塞技术债。
5. **测试覆盖**：安装器 `11/11`、forward `15/15`；19 个场景中的大多数仍是静态规则映射，未冒充真实模型执行。
6. **实际运行结果**：官方结构校验、candidate/baseline/known-bad、真实 forward、记录校验、fixture RED、diff/cache 检查均有新鲜证据；GitHub Actions run `29537377916` 已在 Ubuntu/Windows 全部通过。

## 五、保留的非阻塞边界

- F4：大多数 `cases.yaml` 场景仍是静态映射；后续可按风险逐步增加真实 Agent cases。
- `run_evals.py` 约 1,146 行，仍有拆分为 artifact/rubric/report/fixture 模块的 P2 技术债。
- 多目标安装不是跨目标全局事务；当前预检能避免已知边界问题导致的部分安装。
- 路径预检与实际文件操作之间仍存在需要平台目录句柄才能彻底消除的理论 TOCTOU 风险。
- Claude Code、Cursor、Gemini CLI 等仅验证目录/桥接兼容，未证明所有客户端模型行为相同。
- 未执行真实付费 API、生产部署、系统级安装或破坏性操作。

## 六、首次最终推送后的 CI 修复闭环

GitHub Actions run `29535953451` 在 Ubuntu/Windows 同时暴露两个阻塞：本地 mixed EOL 与 checkout LF 导致 raw-byte artifact hash 不一致；Windows cp1252 stdout 打印中文时抛出 `UnicodeEncodeError`。

修复提交：`d6476d7`。

| ID | 修复 | 同一 Critic 反向复验 | 状态 |
|---|---|---|---|
| R12 | artifact hash v2 对 UTF-8 文本规范化 EOL，二进制保持 raw bytes | working tree 与 `git archive d6476d7` hash 均为 `02c95241…8458`；LF/CRLF/CR 相等；不同二进制不相等；reference 修改后旧记录 FAIL | Closed |
| R13 | runner 主入口重配 stdout/stderr UTF-8；CI job 设置 `PYTHONUTF8=1` | `PYTHONIOENCODING=cp1252:strict`、`PYTHONUTF8=0` 下，有效记录 exit `0`、无效记录 exit `1`，均输出 UTF-8 JSON 且无 `UnicodeEncodeError` | Closed |

同一 Critic 对 `b3fffeb..d6476d7` 的复验 Verdict 为 `Approve`，新增 P0/P1 为 `0`。修复后的 GitHub Actions run `29537377916` 已在 Ubuntu/Windows 全部通过，包括 forward 严格记录、15 项安全/证据测试、known-bad 阻断、11 项安装测试和 whitespace 门禁。

## 历史发布闭环 Verdict

**Approve**

原 Critic 已复验 F1/F2，二者均 Closed；R12/R13 也已完成双系统 CI 验证。该结论对应已发布的 `v1.0.0`，不自动覆盖后续增量。

## 七、N12 增量审计（2026-07-17）

本轮对已发布文档和参考根进行反向增量审计，发现旧报告在数量口径、当前/历史状态和发布时序上存在新的准确性问题：

| ID | 等级 | 发现 | 修复要求 | 当前状态 |
|---|---|---|---|---|
| A1 | P1 | 报告把参考根描述为“排除 9 个符号链接后的实体目录”，但实际有 2,984 个顶层 reparse entries：2,975 个同名 junction 指向 `.agents\skills`，仅 9 个是例外链接 | 明确区分 15,519 顶层直接入口、15,510 合格顶层入口、129 聚合入口、15,639 结构候选、16,102 字面全递归和两种 `rg` 口径 | Closed；同一文档 Critic 复验各口径 |
| A2 | P1 | 项目报告仍把 symlink 防逃逸、Forward 脱敏、记录强校验和 legacy exclusion 写成当前待做，且最终段落仍写“待推送/待 CI” | 改为“审计前问题 → 已关闭”，统一历史发布基线和当前增量时序 | Closed；当前/历史事实已分离 |
| A3 | P2 | 文档混用 142/141 行与 1,561/1,560 行 | 统一为 `SKILL.md` 141 行、`system-prompt.md` 1,560 行 | Closed；实际行数复核一致 |
| A4 | P2 | 轻量 frontmatter 报告误称 `nopua` 无 frontmatter，并遗漏 `spec-driven-eval` 的可观察价值 | 修正 `nopua` 事实；将 `spec-driven-eval` 作为 P2 观察项，不机械并入主方案 | Closed |
| A5 | P1 | Fixture tree 使用宿主 `Path` 排序，Windows/Linux 对大小写路径顺序不同，导致同内容指纹漂移 | POSIX 相对名排序、UTF-8 EOL canonical tree hash、固定跨平台 fixture hash | Closed；Eval Critic 复验 `23/23` |
| A6 | P1 | Candidate 只哈希拼接文本，reference 仅重命名时 fingerprint 不失效 | Candidate/Baseline canonical tree SHA-256 纳入输入指纹；新增 rename 回归 | Closed；重命名同时改变 tree hash 和 fingerprint |
| A7 | P1 | `SKILL.md` 的 `python scripts/install_skill.py` 隐含错误工作目录 | 先解析当前技能目录为 `<skill-dir>`，再调用脚本 | Closed；文档 Critic 复验 |
| A8 | P2 | CLI 摘要绝对路径、兼容长协议刚性规则和 16,102 遍历定义不够严谨 | 摘要脱敏；模块化契约优先；记录 Python 3.11 并集算法 | Closed；两个原 Critic 均复验 |
| A9 | P1 | README 已锁定 `v1.0.1`，但 tag、Release、三个附件和最终双 OS CI 尚未物化 | 分主题提交推送；最终 SHA/Tag CI；annotated tag；从 tag 构建并核验 ZIP、checksum、provenance；远程 tagged npx | Open；仅剩发布阶段门禁 |

本轮已重新执行两个 fresh-context 真实 Forward 场景；当前完整技能 artifact 为 `7291cc43…b29d`，严格记录验证通过。Eval/Forward 单测 `23/23`、安装器 `11/11`、Candidate `100`、Known-bad `15.8`，但这些本地证据不能代替 A9 的远程发布验证。

## 当前增量 Verdict

**Request Changes — Release Gated**

本地实现、文档和独立复验已清零除发布门禁外的 P0/P1。当前只允许进入分主题提交、推送、远程 CI、annotated tag、Release 附件和 tagged 安装验证；完成 A9 后再由原发布/文档 Critic 最终签收。
