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

- Coverage tool + threshold: 仓库未配置 coverage 工具或门槛；本轮只使用环境中已有的 `coverage.py` 做临时诊断，没有把它新增为项目依赖。
- Current reported coverage: 官方/版本化覆盖率仍为 N/A。历史 N13 对 `run_evals.py` 与旧版 `run_forward_tests.py` 的 23 个单元测试执行 branch coverage，合计 `82%`；该诊断不覆盖本版本新增 matrix runner，也不等价于整个仓库覆盖率。
- Fresh local audit result（2026-07-17, Asia/Shanghai）:
  - Python syntax: PASS
  - Installer integration: `11/11` PASS
  - Eval/forward unit tests: `35/35` PASS
  - Eval/forward branch coverage diagnostic: `82%`（仅两个 runner；无正式门槛）
  - Eval self-test: PASS
  - Current candidate: PASS，baseline `40.0`，candidate `100.0`，delta `60.0`，default-context reduction `76.7%`
  - Known-bad: 预期 FAIL，candidate `15.8`，exit `1`
  - Forward synthetic self-test: PASS，但明确不是真实 Agent 证据
  - 历史 `v1.0.1` forward record：本版本会因 artifact hash 变化被标记为陈旧，不可作为 `v1.1.0` 通过证据
  - `git diff --check`: PASS
- Known gaps/flaky areas: 19 个场景多数只做静态规则覆盖；真实 Agent 样本有限；Claude Code/Cursor/Gemini 等真实行为未执行。
- Freshness binding: 上述本轮执行结果绑定到 `workflow_status.md` 的 V23；candidate/known-bad 报告写入系统临时目录，未把临时产物提交进仓库。版本化历史报告仅用于结构和既有记录对照。

### 6) Evidence

- `.github/workflows/skill-evals.yml`
- `skills/production-delivery-orchestrator/tests/test_install_skill.py`
- `evals/production-delivery-orchestrator/tests/test_forward_tests.py`
- `evals/production-delivery-orchestrator/tests/test_run_evals.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `evals/production-delivery-orchestrator/cases.yaml`
- `evals/production-delivery-orchestrator/rubric.yaml`
- `workflow_status.md`（V23 当前复核验证台账）
