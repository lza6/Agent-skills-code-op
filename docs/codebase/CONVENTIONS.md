# Coding Conventions

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Files | Python snake_case；技能/契约目录与 Markdown 多为 kebab-case | `run_forward_tests.py`; `validation-contract.md` | `evals/`; `skills/.../references/` |
| Functions/methods | snake_case，动词或动作短语 | `resolve_project_path`; `evaluate_artifact`; `verify_record` | 三个 Python CLI |
| Types/interfaces | Python 类使用 PascalCase；轻量数据对象使用 dataclass | `Artifact`; `CheckResult` | `run_evals.py:94` |
| Constants/env vars | UPPER_SNAKE_CASE | `SKILL_NAME`; `DEFAULT_CANDIDATE`; `ARTIFACT_HASH_DOMAIN` | Python CLI files |

### 2) Formatting and Linting

- Formatter: 未配置 `[TODO]`。
- Linter: 未配置 `[TODO]`。
- Most relevant enforced rules: Python 语法编译、`unittest`、`git diff --check`、CI YAML 执行；没有独立静态类型或风格门禁。
- Run commands: 见 `docs/codebase/STACK.md` 和 `.github/workflows/skill-evals.yml`。

### 3) Import and Module Conventions

- Import grouping/order: `__future__`，随后标准库；仓库没有第三方依赖组。
- Alias vs relative import policy: 工具脚本使用标准库绝对导入；测试通过 `importlib.util.spec_from_file_location` 加载脚本，而非安装为包。
- Public exports/barrel policy: N/A；没有 Python package `__init__.py` 或公共库 API。
- 路径展示使用仓库相对 POSIX 形式；外部路径使用 `external:<label>` 脱敏。

### 4) Error and Logging Conventions

- Error strategy by layer:
  - Installer：顶层捕获异常，stderr 输出中文错误，退出 `1`；成功 `0`。
  - Offline eval：规则不通过退出 `1`，基础设施/输入错误退出 `2`，成功 `0`。
  - Forward harness：case 失败 `1`，未提供真实命令为 `NOT_RUN`/退出 `2`，成功 `0`。
- Logging style and required context fields: 短命 CLI 以 stdout/stderr 和 JSON 摘要为主；版本化报告记录 status、hash、case/check、git diff/status 和限制。
- Sensitive-data redaction rules: forward harness 对 Authorization/Bearer、常见 API key/token/secret 参数及嵌套值递归脱敏；eval 报告隐藏外部绝对路径。

### 5) Testing Conventions

- Test file naming/location rule: `tests/test_*.py`，按被测工具分目录。
- Mocking strategy norm: 安装器优先真实 `TemporaryDirectory` + subprocess + 文件系统；forward 单测使用 `unittest.mock` 隔离命令、timeout 和常量。
- Coverage expectation: 没有覆盖率工具或阈值 `[TODO]`；当前质量门是 11 个安装测试、23 个 eval/forward 测试、known-bad 阻断和报告校验。

### 6) Evidence

- `.github/workflows/skill-evals.yml`
- `skills/production-delivery-orchestrator/scripts/install_skill.py`
- `skills/production-delivery-orchestrator/tests/test_install_skill.py`
- `evals/production-delivery-orchestrator/run_evals.py`
- `evals/production-delivery-orchestrator/run_forward_tests.py`
- `evals/production-delivery-orchestrator/tests/`
