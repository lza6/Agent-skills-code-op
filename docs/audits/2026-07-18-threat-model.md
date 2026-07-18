# Agent-skills-code-op-repo 威胁模型（2026-07-18）

## 范围与假设

范围是 Skill 源码、安装器、离线评测/forward runner、GitHub Actions 和 Release 制品。
它不是对业务 Web/API/租户/支付系统的建模：仓库没有这些运行面。假设 GitHub 仓库和发布制品可被不可信下载者读取，维护者工作站存在其他项目与 CLI 登录态；未确认的企业网络、私有 fork 与签名策略会改变风险等级。

## 系统与信任边界

| 边界 | 资产 | 现有控制 | 残余风险 |
|---|---|---|---|
| Git source → CI/Release | Skill 完整性、tag/provenance | 固定 Actions SHA、quality `needs`、checksum/provenance/attestation | 有写入仓库或 Release 权限的攻击者仍是高影响主体。 |
| Release ZIP → 本地安装器 | 用户文件系统、既有技能 | 路径校验、链接/重解析点控制、journal/rollback、ZIP 限额 | 文件系统 TOCTOU 与平台特性仍是低/中风险。 |
| evaluator/forward runner → 外部 CLI | API/OAuth 凭证、宿主网络与进程 | 默认最小环境、仓库外 env file、显式 unsafe/host-config/proxy opt-in、超时与进程树收敛 | 用户主动打开 host config 后，真实 CLI 的供应链和账户权限成为边界。 |
| 文档/报告 → 维护决策 | 发布状态、测试结论 | current-state 分界、回归测试、维护契约 | 证据会随新变更过时；必须每次重新核验。 |

## 优先威胁与处理

| 优先级 | 滥用路径 | 影响 | 已有/本次缓解 | 后续触发条件 |
|---|---|---|---|---|
| High | 恶意或被替换的发布制品在安装时覆盖路径/跟随链接 | 本地文件损坏、代码执行前置条件 | 安装路径与符号链接限制、事务回滚、release 校验 | 新增目标目录、归档格式或 `--force` 语义时重测。 |
| High | 非隔离真实 Agent 继承宿主凭证、代理或配置 | 凭证暴露、非预期网络/写入 | 默认拒绝；三重/四重显式 opt-in，报告脱敏 | 新 CLI profile、环境变量或 host 配置路径变化时重审。 |
| Medium | 压缩炸弹/成员名绕过耗尽验证资源 | DoS、路径穿越 | 成员数、单成员、总解压尺寸、压缩比和分块 hash 限制 | 阈值改变或新的归档解析器引入时 fuzz/负测。 |
| Medium | 文档把历史或静态分数写成当前真实行为 | 错误发布决策、虚假兼容性承诺 | current-state 边界、支持矩阵和维护契约；回归检查 | 版本、CI、模型/CLI matrix 或测试数变化时更新。 |
| Medium | 并发进程在安装预检与写入间改变目标 | 安装异常或覆盖意外文件 | 预检、journal、rollback；已显式记录 TOCTOU | 威胁模型要求更强保证时评估目录句柄/锁，不能假设零竞态。 |
| Low | 不可信 prompt/仓库文本诱导 Agent 超出范围 | 错误修改、敏感信息访问 | 将源码/外部文本视为数据，规则文件才是指令；最小权限/范围 | 增加外部爬取、自动 PR 或写入工具时提高优先级。 |

## 验收与限制

本模型依据仓库可见代码和本轮测试事实，而不是渗透测试或真实生产攻击演练。它不证明没有漏洞；它要求在安装器、CLI profile、Release、权限或外部集成变化时重新评估。真正的三客户端模型行为仍受 Claude 模型访问和 Gemini 隔离凭证阻塞。
