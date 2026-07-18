# Testing Patterns

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary test framework: Python standard-library `unittest`（CI Python 3.11）。
- Assertion/mocking tools: `unittest.TestCase`、`unittest.mock`、subprocess、`tempfile.TemporaryDirectory`、真实文件系统与 Git fixture。
- Commands:

```bash
python -m unittest discover -s skills/production-delivery-orchestrator/tests -p "test_*.py" -v
python -m unittest discover -s evals/production-delivery-orchestrator/tests -p "test_*.py" -v
python evals/production-delivery-orchestrator/run_evals.py --self-test
python evals/production-delivery-orchestrator/run_evals.py --output-dir <temp-dir> --report-prefix audit
python evals/production-delivery-orchestrator/run_forward_tests.py --self-test
python evals/production-delivery-orchestrator/run_client_matrix.py
```

### 2) Test Layout

- Test file placement pattern:
  - 安装器：`skills/production-delivery-orchestrator/tests/test_install_skill.py`
  - eval/forward：`evals/production-delivery-orchestrator/tests/test_*.py`
  - 行为 fixture 契约：`evals/.../fixtures/video-polling-state-machine/tests/test_polling_contract.py`
- Naming convention: `test_<behavior>`；测试类按工具或关注点命名。
- Setup files and where they run: 无全局 setup；测试各自使用临时目录、动态模块加载和 subprocess。

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | yes | redaction、canonical hash、record schema、portable paths、route/fingerprint helpers | 部分通过 `unittest.mock` 隔离 |
| Integration | yes | 安装到临时用户/项目目录、force/dry-run、桥接、symlink/junction、Git fixture | 真实 subprocess 与文件系统 |
| E2E / behavior | partial | 两个历史真实 Agent forward cases；synthetic harness；跨 CLI probe-only matrix；known-bad | 未覆盖所有 19 个 prompt 和所有客户端 |
| Cross-platform | yes | Ubuntu/Windows、Python 3.11 | GitHub Actions matrix |

### 4) Mocking and Isolation Strategy

- Main mocking approach: 只在 forward 单测中 mock subprocess/timeout/常量；安装器测试优先真实临时目录和进程。
- Isolation guarantees: `TemporaryDirectory` 自动清理；forward harness 复制 fixture 并初始化独立 Git 仓库；测试不写用户真实目录。
- Common failure mode in tests: Windows symlink 权限可能导致测试 skip；本机本轮 11 个安装测试和 23 个 eval/forward 测试均未显示 skip。
- Fixture `test_polling_contract.py` 在未修复样例中预期 RED；它是缺陷探针，不是主产品回归失败。

### 5) Coverage and Quality Signals

#### 当前复核（2026-07-18，HEAD `eb3bf18`）

- installer/inventory test：`25/25` PASS。
- eval/forward/client-matrix test：`39/39` PASS（`run_evals` 12、`run_forward_tests` 20、`run_client_matrix` 7）。
- release builder test：`5/5` PASS。
- eval self-test：PASS，且 `llm_calls: 0`；forward self-test：PASS，但仅是 synthetic harness。
- current candidate eval：baseline `31.2`、candidate `100.0`、delta `68.8`、default-context reduction `72.5%`；known-bad candidate `12.3`，以预期 exit `1` 失败。
- 没有新的正式 coverage 门槛，也没有本轮真实多客户端 Agent 行为证据。下方 2026-07-17/N13 数字是历史快照，不能覆盖本小节。

#### P0/P1 实施后复验（2026-07-18，基线 `eb3bf18` 的未提交实现）

- workflow governance：`6/6` PASS；installer/inventory：`25/25` PASS；eval/forward/client matrix：Windows 为 49 项、47 PASS、2 条 Linux subreaper 回归 skip；Ubuntu WSL 两条 Linux 专用回归 `2/2` PASS；release builder：`7/7` PASS。
- current candidate：baseline `31.2`、candidate `100.0`、delta `68.8`；known-bad candidate `12.3`，预期 exit `1`。
- forward 的进程树和输出上限仅使用安全本地 Python stub 验收；self-test 仍是 synthetic，不是实际 Agent/多客户端行为结论。
- `release/build_release.py --verify`、Python compile 和 `git diff --check` 均通过。细节及外部发布门见 `docs/implementation-closure-2026-07-18.md`。

- Coverage audit: 版本化 [stdlib trace line baseline](../coverage-baseline.json) 只审计 eval runners 的非空非注释源码行；它不引入第三方依赖，也不宣称 branch coverage 或真实 Agent 行为。CI 在 Linux 上重新采样并拒绝低于文件中 minimum 的结果。
- Current reported coverage: 该 baseline 的首次观测为 matrix `56.57%`、eval `67.18%`、forward `62.86%`；门槛为相应的 `55%`、`65%`、`61%`。历史 N13 的 `82%` 仍只是旧版两个 runner 的临时 branch coverage 诊断，不能与本审计口径混用。
- Historical N13 local audit result（2026-07-17, Asia/Shanghai；不是当前复核）:
  - Python syntax: PASS
  - Installer integration: `11/11` PASS
  - Eval/forward unit tests: `35/35` PASS
  - Eval/forward branch coverage diagnostic: `82%`（仅两个 runner；无正式门槛）
  - Eval self-test: PASS
  - Historical candidate: PASS，baseline `40.0`，candidate `100.0`，delta `60.0`，default-context reduction `76.7%`
  - Known-bad: 预期 FAIL，candidate `15.8`，exit `1`
  - Forward synthetic self-test: PASS，但明确不是真实 Agent 证据
  - 历史 `v1.0.1` forward record：本版本会因 artifact hash 变化被标记为陈旧，不可作为 `v1.1.0` 通过证据
  - `git diff --check`: PASS
- Known gaps/flaky areas: 19 个场景多数只做静态规则覆盖；真实 Agent 样本有限；Claude Code/Cursor/Gemini 等真实行为未执行。
- Historical freshness binding: 上述 N13 结果绑定到 `workflow_status.md` 的 V23；candidate/known-bad 报告写入系统临时目录，未把临时产物提交进仓库。当前复核的命令、结果、日期和 HEAD 以本文件顶部“当前复核（2026-07-18）”及 `workflow_status.md` 顶部 B4 为准。

### 6) Evidence

- `.github/workflows/skill-evals.yml`
- `skills/production-delivery-orchestrator/tests/test_install_skill.py`
- `evals/production-delivery-orchestrator/tests/test_forward_tests.py`
- `evals/production-delivery-orchestrator/tests/test_run_evals.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `evals/production-delivery-orchestrator/cases.yaml`
- `evals/production-delivery-orchestrator/rubric.yaml`
- `workflow_status.md`（顶部 B4 为当前复核验证台账；V23 为历史 N13 台账）
