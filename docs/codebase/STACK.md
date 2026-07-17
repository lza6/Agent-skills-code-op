# Technology Stack

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language | Markdown（技能产品与契约）；Python（安装、评测与测试工具） | `skills/production-delivery-orchestrator/SKILL.md`; `evals/production-delivery-orchestrator/run_evals.py` |
| Runtime + version | Python 3.11 是当前唯一 CI 验证版本；正式最低版本未声明 `[TODO]` | `.github/workflows/skill-evals.yml` |
| Package manager | N/A：仓库没有 `pyproject.toml`、`requirements.txt`、`package.json` 等依赖清单 | `docs/codebase/.codebase-scan.txt`; repository root |
| Module/build system | 无应用构建；Python 标准库 CLI + Agent Skills 目录结构 + GitHub Actions | `.github/workflows/skill-evals.yml`; `skills/production-delivery-orchestrator/` |

### 2) Production Frameworks and Dependencies

仓库没有第三方运行时依赖或 Web/ORM 框架。高影响运行依赖如下。

| Dependency | Version | Role in system | Evidence |
|------------|---------|----------------|----------|
| Python standard library | Python 3.11 CI | `argparse`、`pathlib`、`shutil`、`subprocess`、`unittest` 等 CLI、文件和评测能力 | `install_skill.py`; `run_evals.py`; `run_forward_tests.py` |
| Git CLI | `[TODO]` 未声明最低版本 | 从历史提交直接加载 baseline、初始化和检查 forward-test fixture | `evals/production-delivery-orchestrator/run_evals.py:348`; `run_forward_tests.py:279` |
| Agent Skills-compatible client | 客户端版本未固定 `[TODO]` | 消费 `SKILL.md`、frontmatter、references 和客户端元数据 | `README.md`; `skills/production-delivery-orchestrator/SKILL.md` |

`npx skills` 是面向消费者的安装渠道，不是仓库 Python 代码的生产依赖。

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| Python `unittest` | 安装器、forward harness、报告可移植性和安全回归 | `skills/production-delivery-orchestrator/tests/`; `evals/production-delivery-orchestrator/tests/` |
| Custom offline eval runner | baseline/candidate、触发代理、能力路由、known-bad 和 fixture 检查 | `evals/production-delivery-orchestrator/run_evals.py`; `rubric.yaml` |
| Custom forward-test harness | synthetic 自测、可选真实 Agent CLI、记录校验和脱敏 | `evals/production-delivery-orchestrator/run_forward_tests.py` |
| GitHub Actions | Windows/Ubuntu、Python 3.11 CI | `.github/workflows/skill-evals.yml` |
| Git | baseline、diff、状态和发布证据 | `run_evals.py`; `run_forward_tests.py`; `workflow_status.md` |

### 4) Key Commands

```bash
# 无安装依赖步骤
python -m unittest discover -s skills/production-delivery-orchestrator/tests -p "test_*.py" -v
python -m unittest discover -s evals/production-delivery-orchestrator/tests -p "test_*.py" -v
python evals/production-delivery-orchestrator/run_evals.py --self-test
python evals/production-delivery-orchestrator/run_evals.py --output-dir <temp-dir> --report-prefix audit
python evals/production-delivery-orchestrator/run_forward_tests.py --self-test
python evals/production-delivery-orchestrator/run_forward_tests.py --verify-record evals/production-delivery-orchestrator/reports/forward-tests.json
git diff --check
```

默认 `run_evals.py` 会从 Git 提交 `b3d9a17` 读取发布 baseline；因此仓库必须包含该提交的完整历史。浅克隆或 GitHub 自动生成的 Source archive 需要显式传入可用的 `--baseline`，否则默认命令会失败。CI 使用 `actions/checkout` 的 `fetch-depth: 0` 满足这一条件。

### 5) Environment and Config

- Config sources: `SKILL.md` YAML frontmatter、`agents/openai.yaml`、`evals/.../cases.yaml`、`rubric.yaml`、CLI 参数、GitHub Actions YAML。
- Required env vars: 运行代码没有必需业务环境变量；CI 设置 `PYTHONUTF8=1`。测试时可设置 `PYTHONDONTWRITEBYTECODE=1` 避免缓存文件。
- Deployment/runtime constraints: 技能通过目录复制、`npx skills` 或项目桥接分发；真实 forward-test 需要用户显式提供 `--agent-command`。
- Default eval history constraint: `run_evals.py` 固定默认 baseline ref `b3d9a17`；默认评测要求当前目录是包含该提交的完整 Git 仓库。
- Python 最低版本、支持客户端版本矩阵和 Git 最低版本尚未机器化声明 `[TODO]`。

### 6) Evidence

- `README.md`
- `.github/workflows/skill-evals.yml`
- `skills/production-delivery-orchestrator/SKILL.md`
- `skills/production-delivery-orchestrator/scripts/install_skill.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `docs/codebase/.codebase-scan.txt`
